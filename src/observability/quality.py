from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def _freshness_payload(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    total_rows = int(len(df))
    if total_rows == 0:
        return {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "threshold_days": settings.freshness_threshold_days,
            "max_stale_ratio": 0.25,
            "is_fresh": False,
        }

    if "age_days" in df.columns:
        ages = pd.to_numeric(df["age_days"], errors="coerce")
    else:
        if "published" not in df.columns:
            ages = pd.Series([float("nan")] * total_rows, index=df.index, dtype=float)
        else:
            published = pd.to_datetime(df["published"], errors="coerce", utc=True)
            today = datetime.now(timezone.utc).date()
            ages = published.map(lambda value: (today - value.date()).days if not pd.isna(value) else float("nan"))

    stale_rows = int((ages > settings.freshness_threshold_days).fillna(False).sum())
    if "published" in df.columns:
        published_dates = pd.to_datetime(df["published"], errors="coerce", utc=True).dropna()
    else:
        published_dates = pd.Series(dtype="datetime64[ns, UTC]")
    latest = published_dates.max().date().isoformat() if not published_dates.empty else None
    oldest = published_dates.min().date().isoformat() if not published_dates.empty else None
    stale_ratio = stale_rows / total_rows
    return {
        "latest_published": latest,
        "oldest_published": oldest,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": 0.25,
        "is_fresh": stale_ratio <= 0.25,
    }


def _manual_expectation_results(df: pd.DataFrame) -> list[dict[str, Any]]:
    row_count = len(df)
    required_columns = ["paper_id", "title", "text_for_embedding"]
    not_null_success = all(column in df.columns and not df[column].isna().any() for column in required_columns)
    unique_success = "paper_id" in df.columns and bool(df["paper_id"].is_unique)
    summary_lengths = df["summary"].fillna("").astype(str).str.len() if "summary" in df.columns else pd.Series(dtype=int)
    length_success = "summary" in df.columns and bool((summary_lengths >= 30).all())
    return [
        {
            "type": "ExpectTableRowCountToBeBetween",
            "success": 5 <= row_count <= 5000,
            "observed_value": row_count,
            "min_value": 5,
            "max_value": 5000,
        },
        {
            "type": "ExpectColumnValuesToNotBeNull",
            "success": not_null_success,
            "columns": required_columns,
        },
        {
            "type": "ExpectColumnValuesToBeUnique",
            "success": unique_success,
            "column": "paper_id",
        },
        {
            "type": "ExpectColumnValueLengthsToBeBetween",
            "success": length_success,
            "column": "summary",
            "min_value": 30,
        },
    ]


def _json_safe_validation_result(result: Any) -> dict[str, Any]:
    if hasattr(result, "to_json_dict"):
        payload = result.to_json_dict()
    elif hasattr(result, "model_dump"):
        payload = result.model_dump()
    else:
        payload = {"success": bool(getattr(result, "success", False)), "result": str(result)}
    return json.loads(json.dumps(payload, default=str))


def _run_gx_expectations(df: pd.DataFrame) -> list[dict[str, Any]]:
    import great_expectations as gx

    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    expectations = [
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="title"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]
    results: list[dict[str, Any]] = []
    for expectation in expectations:
        validation = batch.validate(expectation)
        payload = _json_safe_validation_result(validation)
        results.append(
            {
                "type": expectation.__class__.__name__,
                "success": bool(payload.get("success", getattr(validation, "success", False))),
                "validation": payload,
            }
        )
    return results


def _quality_report_path(settings: Settings, report_name: str) -> Path:
    key = report_name.strip().lower().replace("-", "_")
    known_paths = {
        "baseline": settings.paths.baseline_quality_report,
        "clean": settings.paths.baseline_quality_report,
        "corrupted": settings.paths.corrupted_quality_report,
        "corruption": settings.paths.corrupted_quality_report,
    }
    return known_paths.get(key, settings.paths.quality_dir / f"{key or 'quality'}_quality_report.json")


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Validate required data expectations with GX 1.x and apply the freshness SLA."""
    gx_error: str | None = None
    try:
        expectation_results = _run_gx_expectations(df)
        engine = "great_expectations_1.x"
    except Exception as exc:
        # Keep diagnostics available even in a partially installed student environment.
        expectation_results = _manual_expectation_results(df)
        gx_error = f"{type(exc).__name__}: {exc}"
        engine = "pandas_fallback"

    freshness = _freshness_payload(df, settings)
    expectations_success = all(bool(result["success"]) for result in expectation_results)
    result: dict[str, Any] = {
        "report_name": report_name,
        "engine": engine,
        "row_count": int(len(df)),
        "expectations_success": expectations_success,
        "freshness_success": freshness["is_fresh"],
        "success": expectations_success and freshness["is_fresh"],
        "expectations": expectation_results,
        "freshness": freshness,
    }
    if gx_error:
        result["gx_error"] = gx_error
    write_json(_quality_report_path(settings, report_name), result)
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Measure stale-record share and persist the Freshness SLA result."""
    report = _freshness_payload(df, settings)
    report["report_date"] = datetime.now(timezone.utc).date().isoformat()
    if report_path is not None:
        write_json(Path(report_path), report)
    return report
