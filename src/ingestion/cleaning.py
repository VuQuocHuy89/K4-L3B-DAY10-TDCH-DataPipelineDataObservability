from __future__ import annotations

from datetime import date, datetime, timezone
from html import unescape
import re
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    value = re.sub(r"<[^>]*>", " ", str(value))
    return normalize_whitespace(unescape(value))


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = re.split(r"[,;|]", value)
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]
    result: list[str] = []
    for item in values:
        cleaned = _clean_text(item)
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _published_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        parsed = pd.to_datetime(value, errors="coerce", utc=True)
        if pd.isna(parsed):
            return None
        return parsed.date()
    except (TypeError, ValueError, OverflowError):
        return None


def _as_run_date(value: datetime | date) -> date:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).date()
        return value.date()
    return value


def _embedding_text(title: str, authors: str, published: str, categories: str, summary: str) -> str:
    return "\n".join(
        [
            f"Title: {title}",
            f"Authors: {authors}",
            f"Published: {published}",
            f"Categories: {categories}",
            f"Summary: {summary}",
        ]
    )


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize records, derive embedding text, and remove invalid/duplicate rows."""
    today = _as_run_date(run_date)
    rows: list[dict[str, Any]] = []
    for record in records:
        title = _clean_text(record.title)
        summary = _clean_text(record.summary)
        paper_id = _clean_text(record.paper_id).lower()
        published_date = _published_date(record.published)
        if not paper_id or not title or not summary or published_date is None:
            continue

        authors = _string_list(record.authors)
        categories = _string_list(record.categories)
        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        published = published_date.isoformat()
        text_for_embedding = _embedding_text(title, authors_joined, published, categories_joined, summary)
        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": _clean_text(record.primary_category) or (categories[0] if categories else ""),
                "published": published,
                "updated": _published_date(record.updated).isoformat() if _published_date(record.updated) else published,
                "abs_url": _clean_text(record.abs_url),
                "pdf_url": _clean_text(record.pdf_url),
                "comment": _clean_text(record.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "age_days": (today - published_date).days,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
            }
        )

    columns = [
        "paper_id",
        "title",
        "summary",
        "authors",
        "categories",
        "primary_category",
        "published",
        "updated",
        "abs_url",
        "pdf_url",
        "comment",
        "authors_joined",
        "categories_joined",
        "age_days",
        "summary_chars",
        "text_for_embedding",
    ]
    dataframe = pd.DataFrame(rows, columns=columns)
    if dataframe.empty:
        return dataframe
    dataframe = dataframe.drop_duplicates(subset=["paper_id"], keep="first")
    dataframe = dataframe.sort_values(["published", "paper_id"], kind="stable").reset_index(drop=True)
    return dataframe
