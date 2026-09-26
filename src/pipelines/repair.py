from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks


@dataclass(frozen=True)
class AutoRepairResult:
    """Result of a quality-gate-triggered repair attempt."""

    dataframe: pd.DataFrame | None
    quality: dict[str, Any]
    freshness: dict[str, Any]
    triggered: bool
    reasons: list[str]
    source: str | None
    log_path: Path | None


def _repair_log_path(settings: Settings) -> Path:
    return settings.paths.raw_records_json.parent.parent / "results" / "repair_log.json"


def _failure_reasons(quality: dict[str, Any], freshness: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    failed_expectations = [
        str(item.get("type", "unknown_expectation"))
        for item in quality.get("expectations", [])
        if not item.get("success")
    ]
    reasons.extend(f"quality:{name}" for name in failed_expectations)
    if quality.get("freshness_success") is False:
        reasons.append("quality:freshness")
    if freshness.get("is_fresh") is False and "quality:freshness" not in reasons:
        reasons.append("freshness:sla")
    if not reasons and not quality.get("success", False):
        reasons.append("quality:gate_failed")
    return reasons


def auto_repair_if_needed(
    settings: Settings,
    quality: dict[str, Any],
    freshness: dict[str, Any],
    report_name: str = "repaired",
) -> AutoRepairResult:
    """Repair data automatically when the quality or freshness gate fails.

    The raw normalized records are the rollback anchor. If that artifact is
    unavailable or unreadable, ``fetch_source_records`` performs the configured
    Crossref fetch/snapshot fallback. The repaired frame is validated again
    before the caller is allowed to index or evaluate it.
    """

    reasons = _failure_reasons(quality, freshness)
    if not reasons:
        return AutoRepairResult(
            dataframe=None,
            quality=quality,
            freshness=freshness,
            triggered=False,
            reasons=[],
            source=None,
            log_path=None,
        )

    log_path = _repair_log_path(settings)
    event: dict[str, Any] = {
        "triggered": True,
        "status": "started",
        "reasons": reasons,
        "input_quality_success": bool(quality.get("success")),
        "input_freshness_success": bool(freshness.get("is_fresh")),
        "report_name": report_name,
    }

    try:
        source = "raw_snapshot"
        try:
            records = load_raw_records(settings.paths.raw_records_json)
        except Exception:
            # If the raw anchor is missing/corrupt, use Crossref's live request
            # or its configured offline snapshot fallback.
            records = fetch_source_records(settings)
            source = "crossref_refetch_or_snapshot"

        repaired_df = build_clean_dataframe(records, now_utc())
        if repaired_df.empty:
            raise RuntimeError("Automatic repair produced an empty cleaned dataframe.")

        repaired_quality = run_data_quality_checks(repaired_df, settings, report_name)
        repaired_freshness = build_freshness_report(repaired_df, settings, report_path=None)
        if not repaired_quality.get("success") or not repaired_freshness.get("is_fresh"):
            failed = [
                str(item.get("type", "unknown_expectation"))
                for item in repaired_quality.get("expectations", [])
                if not item.get("success")
            ]
            if not repaired_freshness.get("is_fresh"):
                failed.append("Freshness SLA")
            raise RuntimeError(
                "Automatic repair failed its validation gate: " + ", ".join(failed or ["unknown failure"])
            )

        event.update(
            {
                "status": "repaired",
                "source": source,
                "output_rows": int(len(repaired_df)),
                "quality_success": bool(repaired_quality.get("success")),
                "freshness_success": bool(repaired_freshness.get("is_fresh")),
            }
        )
        write_json(log_path, event)
        return AutoRepairResult(
            dataframe=repaired_df,
            quality=repaired_quality,
            freshness=repaired_freshness,
            triggered=True,
            reasons=reasons,
            source=source,
            log_path=log_path,
        )
    except Exception as exc:
        event.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        write_json(log_path, event)
        raise RuntimeError(f"Automatic repair could not restore a valid dataset; see {log_path}.") from exc
