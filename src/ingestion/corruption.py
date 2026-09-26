from __future__ import annotations

from datetime import date, timedelta
import math
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def _paper_ids(frame: pd.DataFrame) -> list[str]:
    return [str(value) for value in frame.get("paper_id", pd.Series(dtype=str)).tolist()]


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


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Apply six deterministic data failures and save an auditable corruption log."""
    if df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")
    corrupted = df.copy(deep=True).reset_index(drop=True)
    events: list[dict[str, Any]] = []

    # Remove the newest fifth of the corpus, modeling a missed ingestion window.
    published_dates = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
    newest_first = published_dates.sort_values(ascending=False, kind="stable").index
    drop_count = min(len(corrupted) - 1, max(1, math.ceil(len(corrupted) * 0.20)))
    dropped_indexes = list(newest_first[:drop_count])
    dropped_ids = _paper_ids(corrupted.loc[dropped_indexes])
    corrupted = corrupted.drop(index=dropped_indexes).reset_index(drop=True)
    events.append(
        {
            "type": "drop_latest_records",
            "description": "Removed the newest 20% of records by publication date.",
            "count": len(dropped_ids),
            "paper_ids": dropped_ids,
        }
    )

    # Keep subsequent mutations deterministic and separate so every failure is visible.
    corrupted = corrupted.sort_values("paper_id", kind="stable").reset_index(drop=True)
    total = len(corrupted)
    per_group = max(1, math.ceil(total * 0.20))

    blank_indexes = [0]
    blank_ids = _paper_ids(corrupted.loc[blank_indexes])
    corrupted.loc[blank_indexes, "summary"] = ""
    events.append(
        {
            "type": "blank_summary",
            "description": "Blanked the summary of a record.",
            "count": len(blank_ids),
            "paper_ids": blank_ids,
        }
    )

    noise_start = 1
    noise_indexes = list(range(noise_start, min(noise_start + per_group, total)))
    noise_ids = _paper_ids(corrupted.loc[noise_indexes])
    for index in noise_indexes:
        summary = str(corrupted.at[index, "summary"])
        corrupted.at[index, "summary"] = f"{summary} ### %% CORRUPTION_NOISE_7xQ @@@"
    events.append(
        {
            "type": "inject_summary_noise",
            "description": "Appended synthetic non-semantic characters to summaries.",
            "count": len(noise_ids),
            "paper_ids": noise_ids,
        }
    )

    title_start = noise_start + per_group
    title_indexes = list(range(title_start, min(title_start + per_group, total)))
    title_ids = _paper_ids(corrupted.loc[title_indexes])
    for index in title_indexes:
        corrupted.at[index, "title"] = str(corrupted.at[index, "title"])[:7]
    events.append(
        {
            "type": "truncate_title",
            "description": "Truncated titles to fewer than eight characters.",
            "count": len(title_ids),
            "paper_ids": title_ids,
        }
    )

    # Make every surviving record stale so the SLA alert is deterministic.
    stale_ids = _paper_ids(corrupted)
    corrupted["published"] = corrupted["published"].map(
        lambda value: (date.fromisoformat(str(value)[:10]) - timedelta(days=365)).isoformat()
    )
    corrupted["age_days"] = pd.to_numeric(corrupted["age_days"], errors="coerce").fillna(0).astype(int) + 365
    events.append(
        {
            "type": "stale_publication_date",
            "description": "Moved publication dates back by 365 days and increased age_days accordingly.",
            "count": len(stale_ids),
            "paper_ids": stale_ids,
        }
    )

    duplicate_count = max(1, math.ceil(len(corrupted) * 0.20))
    duplicated = corrupted.head(duplicate_count).copy(deep=True)
    duplicate_ids = _paper_ids(duplicated)
    corrupted = pd.concat([corrupted, duplicated], ignore_index=True)
    events.append(
        {
            "type": "duplicate_rows",
            "description": "Appended duplicate copies of 20% of the surviving records.",
            "count": len(duplicate_ids),
            "paper_ids": duplicate_ids,
        }
    )

    _refresh_derived_fields(corrupted)
    log = {
        "input_rows": int(len(df)),
        "output_rows": int(len(corrupted)),
        "events": events,
    }
    write_json(Path(output_log_path), log)
    return corrupted
