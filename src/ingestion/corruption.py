from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
import math
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


@dataclass(frozen=True)
class CorruptionConfig:
    """Severity of the six injected failures; the defaults reproduce the lab's reference run."""

    drop_latest_ratio: float = 0.20
    blank_summary_rows: int = 1
    # Share of surviving rows hit by summary noise, and separately by title truncation.
    group_ratio: float = 0.20
    noise_suffix: str = " ### %% CORRUPTION_NOISE_7xQ @@@"
    truncated_title_length: int = 7
    stale_shift_days: int = 365
    duplicate_ratio: float = 0.20

    def __post_init__(self) -> None:
        for name in ("drop_latest_ratio", "group_ratio", "duplicate_ratio"):
            value = getattr(self, name)
            if not 0 < value <= 1:
                raise ValueError(f"{name} must be in (0, 1], got {value}.")
        if self.blank_summary_rows < 1:
            raise ValueError("blank_summary_rows must be at least 1.")
        if not 0 < self.truncated_title_length < 8:
            raise ValueError("truncated_title_length must be between 1 and 7 (titles shorter than 8 characters).")
        if self.stale_shift_days < 1:
            raise ValueError("stale_shift_days must be positive.")
        if not self.noise_suffix.strip():
            raise ValueError("noise_suffix must contain visible characters.")


# Checks in observability/quality.py expected to flag each failure under the default config.
# An empty list marks a silent failure: the data passes the gate but still degrades the RAG answers.
EXPECTED_DETECTORS: dict[str, list[str]] = {
    "drop_latest_records": [],
    "blank_summary": ["ExpectColumnValueLengthsToBeBetween(summary, min_value=30)"],
    "inject_summary_noise": [],
    "truncate_title": [],
    "stale_publication_date": ["Freshness SLA (age_days > 180 for more than 25% of rows)"],
    "duplicate_rows": ["ExpectColumnValuesToBeUnique(paper_id)"],
}

_PREVIEW_CHARS = 60


def _preview(text: str) -> str:
    return text if len(text) <= _PREVIEW_CHARS else text[: _PREVIEW_CHARS - 3] + "..."


def _tail(text: str) -> str:
    return text if len(text) <= _PREVIEW_CHARS else "..." + text[-(_PREVIEW_CHARS - 3) :]


def _paper_ids(frame: pd.DataFrame) -> list[str]:
    return [str(value) for value in frame.get("paper_id", pd.Series(dtype=str)).tolist()]


def _event(event_type: str, description: str, paper_ids: list[str], changes: list[dict[str, Any]]) -> dict[str, Any]:
    detectors = EXPECTED_DETECTORS[event_type]
    return {
        "type": event_type,
        "description": description,
        "count": len(paper_ids),
        "paper_ids": paper_ids,
        "expected_detectors": list(detectors),
        "silent": not detectors,
        "changes": changes,
    }


def _change(paper_id: Any, field: str, before: Any, after: Any) -> dict[str, Any]:
    return {"paper_id": str(paper_id), "field": field, "before": before, "after": after}


def _refresh_derived_fields(frame: pd.DataFrame) -> None:
    for index, row in frame.iterrows():
        frame.at[index, "summary_chars"] = len(str(row.get("summary", "")))
        frame.at[index, "text_for_embedding"] = "\n".join(
            [
                f"Title: {row.get('title', '')}",
                f"Authors: {row.get('authors_joined', '')}",
                f"Published: {row.get('published', '')}",
                f"Categories: {row.get('categories_joined', '')}",
                f"Summary: {row.get('summary', '')}",
            ]
        )


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path,
    config: CorruptionConfig | None = None,
) -> pd.DataFrame:
    """Apply six deterministic data failures and save an auditable corruption log."""
    if df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")
    config = config or CorruptionConfig()
    corrupted = df.copy(deep=True).reset_index(drop=True)
    events: list[dict[str, Any]] = []

    # Remove the newest fifth of the corpus, modeling a missed ingestion window.
    published_dates = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
    newest_first = published_dates.sort_values(ascending=False, kind="stable").index
    drop_count = min(len(corrupted) - 1, max(1, math.ceil(len(corrupted) * config.drop_latest_ratio)))
    dropped_indexes = list(newest_first[:drop_count])
    dropped_ids = _paper_ids(corrupted.loc[dropped_indexes])
    dropped_changes = [
        _change(corrupted.at[index, "paper_id"], "row", f"published {corrupted.at[index, 'published']}", "dropped")
        for index in dropped_indexes
    ]
    corrupted = corrupted.drop(index=dropped_indexes).reset_index(drop=True)
    events.append(
        _event(
            "drop_latest_records",
            f"Removed the newest {config.drop_latest_ratio:.0%} of records by publication date.",
            dropped_ids,
            dropped_changes,
        )
    )

    # Keep subsequent mutations deterministic and separate so every failure is visible.
    corrupted = corrupted.sort_values("paper_id", kind="stable").reset_index(drop=True)
    total = len(corrupted)
    per_group = max(1, math.ceil(total * config.group_ratio))

    blank_indexes = list(range(min(config.blank_summary_rows, total)))
    blank_ids = _paper_ids(corrupted.loc[blank_indexes])
    blank_changes = [
        _change(corrupted.at[index, "paper_id"], "summary", _preview(str(corrupted.at[index, "summary"])), "")
        for index in blank_indexes
    ]
    corrupted.loc[blank_indexes, "summary"] = ""
    events.append(_event("blank_summary", "Blanked the summary of a record.", blank_ids, blank_changes))

    noise_start = len(blank_indexes)
    noise_indexes = list(range(noise_start, min(noise_start + per_group, total)))
    noise_ids = _paper_ids(corrupted.loc[noise_indexes])
    noise_changes: list[dict[str, Any]] = []
    for index in noise_indexes:
        summary = str(corrupted.at[index, "summary"])
        corrupted.at[index, "summary"] = f"{summary}{config.noise_suffix}"
        noise_changes.append(
            _change(corrupted.at[index, "paper_id"], "summary", _tail(summary), _tail(corrupted.at[index, "summary"]))
        )
    events.append(
        _event(
            "inject_summary_noise",
            "Appended synthetic non-semantic characters to summaries.",
            noise_ids,
            noise_changes,
        )
    )

    title_start = noise_start + per_group
    title_indexes = list(range(title_start, min(title_start + per_group, total)))
    title_ids = _paper_ids(corrupted.loc[title_indexes])
    title_changes: list[dict[str, Any]] = []
    for index in title_indexes:
        title = str(corrupted.at[index, "title"])
        corrupted.at[index, "title"] = title[: config.truncated_title_length]
        title_changes.append(_change(corrupted.at[index, "paper_id"], "title", title, corrupted.at[index, "title"]))
    events.append(
        _event(
            "truncate_title",
            "Truncated titles to fewer than eight characters.",
            title_ids,
            title_changes,
        )
    )

    # Make every surviving record stale so the SLA alert is deterministic.
    stale_ids = _paper_ids(corrupted)
    original_published = corrupted["published"].tolist()
    corrupted["published"] = corrupted["published"].map(
        lambda value: (date.fromisoformat(str(value)[:10]) - timedelta(days=config.stale_shift_days)).isoformat()
    )
    corrupted["age_days"] = (
        pd.to_numeric(corrupted["age_days"], errors="coerce").fillna(0).astype(int) + config.stale_shift_days
    )
    stale_changes = [
        _change(paper_id, "published", str(before), after)
        for paper_id, before, after in zip(stale_ids, original_published, corrupted["published"].tolist())
    ]
    events.append(
        _event(
            "stale_publication_date",
            f"Moved publication dates back by {config.stale_shift_days} days and increased age_days accordingly.",
            stale_ids,
            stale_changes,
        )
    )

    duplicate_count = max(1, math.ceil(len(corrupted) * config.duplicate_ratio))
    duplicated = corrupted.head(duplicate_count).copy(deep=True)
    duplicate_ids = _paper_ids(duplicated)
    corrupted = pd.concat([corrupted, duplicated], ignore_index=True)
    events.append(
        _event(
            "duplicate_rows",
            f"Appended duplicate copies of {config.duplicate_ratio:.0%} of the surviving records.",
            duplicate_ids,
            [_change(paper_id, "row", "1 copy", "2 copies") for paper_id in duplicate_ids],
        )
    )

    _refresh_derived_fields(corrupted)
    log = {
        "input_rows": int(len(df)),
        "output_rows": int(len(corrupted)),
        "config": asdict(config),
        "silent_failures": [event["type"] for event in events if event["silent"]],
        "events": events,
    }
    write_json(Path(output_log_path), log)
    return corrupted
