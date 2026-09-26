from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from html import unescape
import json
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"<[^>]*>", " ", text)
    return normalize_whitespace(unescape(text))


def _first_text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        for item in value:
            cleaned = _clean_text(item)
            if cleaned:
                return cleaned
        return ""
    return _clean_text(value)


def _date_value(value: Any) -> str:
    """Read the partial dates used by Crossref and return an ISO date."""
    if isinstance(value, dict):
        parts = value.get("date-parts") or value.get("date_parts")
        if parts and isinstance(parts[0], (list, tuple)) and parts[0]:
            parts = parts[0]
            try:
                year = int(parts[0])
                month = int(parts[1]) if len(parts) > 1 else 1
                day = int(parts[2]) if len(parts) > 2 else 1
                return date(year, month, day).isoformat()
            except (TypeError, ValueError, OverflowError):
                return ""
        value = value.get("date-time") or value.get("date_time") or value.get("timestamp")
    if isinstance(value, (list, tuple)) and value:
        return _date_value({"date-parts": [value]})
    if isinstance(value, (datetime, date)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return ""
        try:
            return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            match = re.match(r"^(\d{4})(?:[-/](\d{1,2}))?(?:[-/](\d{1,2}))?", cleaned)
            if match:
                year, month, day = match.groups()
                try:
                    return date(int(year), int(month or 1), int(day or 1)).isoformat()
                except ValueError:
                    return ""
    return ""


def _authors(item: dict[str, Any]) -> list[str]:
    authors = item.get("author") or item.get("authors") or []
    if isinstance(authors, str):
        authors = [authors]
    result: list[str] = []
    for author in authors:
        if isinstance(author, str):
            name = _clean_text(author)
        elif isinstance(author, dict):
            name = _clean_text(author.get("name"))
            if not name:
                name = _clean_text(" ".join(part for part in (author.get("given"), author.get("family")) if part))
        else:
            name = ""
        if name and name not in result:
            result.append(name)
    return result


def _categories(item: dict[str, Any]) -> list[str]:
    categories = item.get("subject") or item.get("categories") or []
    if isinstance(categories, str):
        categories = [categories]
    result: list[str] = []
    for category in categories:
        cleaned = _clean_text(category)
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _record_from_item(item: dict[str, Any]) -> PaperRecord | None:
    paper_id = _clean_text(item.get("DOI") or item.get("doi") or item.get("paper_id")).lower()
    title = _first_text(item.get("title"))
    summary = _clean_text(item.get("abstract") or item.get("summary") or item.get("description"))
    if not paper_id or not title or not summary:
        return None

    authors = _authors(item)
    categories = _categories(item)
    published = (
        _date_value(item.get("published"))
        or _date_value(item.get("published-print"))
        or _date_value(item.get("published-online"))
        or _date_value(item.get("published_date"))
    )
    if not published:
        return None

    updated = (
        _date_value(item.get("updated"))
        or _date_value(item.get("indexed"))
        or _date_value(item.get("created"))
        or published
    )
    abs_url = _clean_text(item.get("URL") or item.get("url") or item.get("abs_url"))
    if not abs_url:
        abs_url = f"https://doi.org/{paper_id}"

    pdf_url = _clean_text(item.get("pdf_url"))
    if not pdf_url:
        for link in item.get("link", []) or []:
            if not isinstance(link, dict):
                continue
            content_type = str(link.get("content-type", "")).lower()
            if "pdf" in content_type:
                pdf_url = _clean_text(link.get("URL"))
                if pdf_url:
                    break
    comment = item.get("comment") or ""
    if isinstance(comment, list):
        comment = " ".join(_clean_text(value) for value in comment)

    return PaperRecord(
        paper_id=paper_id,
        title=title,
        summary=summary,
        authors=authors,
        categories=categories,
        primary_category=categories[0] if categories else "",
        published=published,
        updated=updated,
        abs_url=abs_url,
        pdf_url=pdf_url or abs_url,
        comment=_clean_text(comment),
    )


def parse_crossref_payload(payload: dict[str, Any]) -> list[PaperRecord]:
    """Parse Crossref's work-list response into validated paper records."""
    if isinstance(payload, list):
        items = payload
    else:
        message = payload.get("message", payload)
        items = message.get("items", []) if isinstance(message, dict) else []

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        record = _record_from_item(item)
        if record:
            records.append(record)
    return records


def _load_snapshot(settings: Settings) -> tuple[list[PaperRecord], str] | None:
    """Load the checked-in offline snapshot, preferring the raw API response."""
    raw_path = settings.paths.raw_api_response
    if raw_path.exists():
        try:
            payload = json.loads(raw_path.read_text(encoding="utf-8"))
            records = parse_crossref_payload(payload)
            if records:
                return records, "snapshot"
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    records_path = settings.paths.raw_records_json
    if records_path.exists():
        try:
            records = load_raw_records(records_path)
            if records:
                return records, "raw-records-fallback"
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    return None


def _fetch_live_payload(settings: Settings) -> dict[str, Any]:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": "DOI,title,abstract,author,subject,published,published-print,published-online,created,indexed,URL,link,comment",
    }
    headers = {
        "User-Agent": "Day10-Data-Observability-Lab/1.0",
        "Accept": "application/json",
    }
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get("https://api.crossref.org/works", params=params, headers=headers, timeout=(5, 30))
            if response.status_code in {429, 503} and attempt < 2:
                retry_after = response.headers.get("Retry-After", "")
                try:
                    delay = min(max(float(retry_after), 0.0), 5.0)
                except ValueError:
                    delay = float(attempt + 1)
                time.sleep(delay)
                continue
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(float(attempt + 1))
    raise RuntimeError(f"Crossref API request failed after 3 attempts: {last_error}") from last_error


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Use the local snapshot by default; optionally refresh from Crossref."""
    if not settings.refresh_source:
        # The normalized raw artifact is the repair source of record once it exists.
        if settings.paths.raw_records_json.exists():
            try:
                records = load_raw_records(settings.paths.raw_records_json)
                if records:
                    return records
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                pass
        snapshot = _load_snapshot(settings)
        if snapshot:
            records, _ = snapshot
            if not settings.paths.raw_records_json.exists():
                write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
            return records

    try:
        payload = _fetch_live_payload(settings)
        records = parse_crossref_payload(payload)
        if not records:
            raise RuntimeError("Crossref returned no records with DOI, title, abstract, and publication date.")
        write_json(settings.paths.raw_api_response, payload)
        write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
        return records
    except Exception as api_error:
        snapshot = _load_snapshot(settings)
        if snapshot:
            records, _ = snapshot
            if not settings.paths.raw_records_json.exists():
                write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
            return records
        raise RuntimeError(f"Could not fetch Crossref data and no usable local snapshot exists: {api_error}") from api_error


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Read serialized PaperRecord objects or a raw Crossref response."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return parse_crossref_payload(payload)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of raw records in {path}.")

    records: list[PaperRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        # Accept both our normalized schema and native Crossref work objects.
        if "paper_id" not in item:
            record = _record_from_item(item)
        else:
            record = PaperRecord(
                paper_id=_clean_text(item.get("paper_id")).lower(),
                title=_clean_text(item.get("title")),
                summary=_clean_text(item.get("summary")),
                authors=[_clean_text(value) for value in item.get("authors", []) if _clean_text(value)],
                categories=[_clean_text(value) for value in item.get("categories", []) if _clean_text(value)],
                primary_category=_clean_text(item.get("primary_category")),
                published=_date_value(item.get("published")),
                updated=_date_value(item.get("updated")) or _date_value(item.get("published")),
                abs_url=_clean_text(item.get("abs_url")),
                pdf_url=_clean_text(item.get("pdf_url")),
                comment=_clean_text(item.get("comment")),
            )
        if record and record.paper_id and record.title and record.summary and record.published:
            records.append(record)
    return records
