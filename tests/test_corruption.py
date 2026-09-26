from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from types import SimpleNamespace

import pandas as pd
import pytest

from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import EXPECTED_DETECTORS, CorruptionConfig, corrupt_clean_dataframe
from ingestion.crossref import PaperRecord
from observability.quality import _freshness_payload, _manual_expectation_results

RUN_DATE = datetime(2026, 9, 1, tzinfo=timezone.utc)
EVENT_TYPES = [
    "drop_latest_records",
    "blank_summary",
    "inject_summary_noise",
    "truncate_title",
    "stale_publication_date",
    "duplicate_rows",
]


@pytest.fixture
def clean_df() -> pd.DataFrame:
    """Ten fresh papers built through the real cleaning step, published 2026-06-01 .. 2026-06-10."""
    records = [
        PaperRecord(
            paper_id=f"10.1000/p{i:02d}",
            title=f"Observability Study Number {i:02d} for RAG Pipelines",
            summary=f"Paper {i:02d} studies data quality gates. It measures retrieval drift over time.",
            authors=[f"Author {i}", "Shared Author"],
            categories=["Data Engineering"],
            primary_category="Data Engineering",
            published=(date(2026, 6, 1) + timedelta(days=i - 1)).isoformat(),
            updated="",
            abs_url=f"https://doi.org/10.1000/p{i:02d}",
            pdf_url="",
            comment="",
        )
        for i in range(1, 11)
    ]
    return build_clean_dataframe(records, RUN_DATE)


def _run(clean_df, tmp_path, config=None):
    log_path = tmp_path / "corruption_log.json"
    corrupted = corrupt_clean_dataframe(clean_df, log_path, config)
    return corrupted, json.loads(log_path.read_text(encoding="utf-8"))


def _event(log, event_type):
    return next(event for event in log["events"] if event["type"] == event_type)


def test_logs_all_six_failures_in_order(clean_df, tmp_path):
    _, log = _run(clean_df, tmp_path)

    assert [event["type"] for event in log["events"]] == EVENT_TYPES
    assert log["input_rows"] == 10
    assert log["config"] == CorruptionConfig().__dict__


def test_default_config_row_counts(clean_df, tmp_path):
    # 10 rows -> drop 2 newest -> 8; noise/title groups of ceil(8 * 0.2) = 2; duplicate 2 -> 10 rows.
    corrupted, log = _run(clean_df, tmp_path)

    counts = {event["type"]: event["count"] for event in log["events"]}
    assert counts == {
        "drop_latest_records": 2,
        "blank_summary": 1,
        "inject_summary_noise": 2,
        "truncate_title": 2,
        "stale_publication_date": 8,
        "duplicate_rows": 2,
    }
    assert len(corrupted) == log["output_rows"] == 10


def test_each_failure_is_applied(clean_df, tmp_path):
    corrupted, log = _run(clean_df, tmp_path)
    by_id = corrupted.drop_duplicates("paper_id").set_index("paper_id")
    original = clean_df.set_index("paper_id")

    assert _event(log, "drop_latest_records")["paper_ids"] == ["10.1000/p10", "10.1000/p09"]
    assert not set(_event(log, "drop_latest_records")["paper_ids"]) & set(corrupted["paper_id"])

    for paper_id in _event(log, "blank_summary")["paper_ids"]:
        assert by_id.at[paper_id, "summary"] == ""

    for paper_id in _event(log, "inject_summary_noise")["paper_ids"]:
        assert by_id.at[paper_id, "summary"].endswith(CorruptionConfig().noise_suffix)

    for paper_id in _event(log, "truncate_title")["paper_ids"]:
        assert len(by_id.at[paper_id, "title"]) < 8

    for paper_id in _event(log, "stale_publication_date")["paper_ids"]:
        shifted = date.fromisoformat(original.at[paper_id, "published"]) - timedelta(days=365)
        assert by_id.at[paper_id, "published"] == shifted.isoformat()
        assert by_id.at[paper_id, "age_days"] == original.at[paper_id, "age_days"] + 365

    assert not corrupted["paper_id"].is_unique
    assert corrupted["paper_id"].duplicated().sum() == _event(log, "duplicate_rows")["count"]


def test_failure_groups_do_not_overlap(clean_df, tmp_path):
    _, log = _run(clean_df, tmp_path)
    groups = [set(_event(log, name)["paper_ids"]) for name in ("blank_summary", "inject_summary_noise", "truncate_title")]

    assert groups[0].isdisjoint(groups[1])
    assert groups[0].isdisjoint(groups[2])
    assert groups[1].isdisjoint(groups[2])


def test_embedding_text_reflects_corruption(clean_df, tmp_path):
    corrupted, log = _run(clean_df, tmp_path)
    by_id = corrupted.drop_duplicates("paper_id").set_index("paper_id")

    for paper_id in _event(log, "truncate_title")["paper_ids"]:
        text = by_id.at[paper_id, "text_for_embedding"]
        assert text.startswith(f"Title: {by_id.at[paper_id, 'title']}\n")
    for paper_id in _event(log, "inject_summary_noise")["paper_ids"]:
        assert "CORRUPTION_NOISE" in by_id.at[paper_id, "text_for_embedding"]
    assert (corrupted["summary_chars"] == corrupted["summary"].str.len()).all()


def test_input_dataframe_is_not_mutated(clean_df, tmp_path):
    snapshot = clean_df.copy(deep=True)
    _run(clean_df, tmp_path)

    pd.testing.assert_frame_equal(clean_df, snapshot)


def test_corruption_is_deterministic(clean_df, tmp_path):
    first = corrupt_clean_dataframe(clean_df, tmp_path / "first.json")
    second = corrupt_clean_dataframe(clean_df, tmp_path / "second.json")

    pd.testing.assert_frame_equal(first, second)
    assert (tmp_path / "first.json").read_text(encoding="utf-8") == (tmp_path / "second.json").read_text(encoding="utf-8")


def test_log_records_before_and_after_values(clean_df, tmp_path):
    _, log = _run(clean_df, tmp_path)

    for event in log["events"]:
        assert len(event["changes"]) == event["count"]
        assert [change["paper_id"] for change in event["changes"]] == event["paper_ids"]
    title_change = _event(log, "truncate_title")["changes"][0]
    assert title_change["after"] == title_change["before"][:7]


def test_detection_metadata_matches_detector_map(clean_df, tmp_path):
    _, log = _run(clean_df, tmp_path)

    for event in log["events"]:
        assert event["expected_detectors"] == EXPECTED_DETECTORS[event["type"]]
        assert event["silent"] is (not EXPECTED_DETECTORS[event["type"]])
    assert log["silent_failures"] == ["drop_latest_records", "inject_summary_noise", "truncate_title"]


def test_quality_gate_flags_only_the_non_silent_failures(clean_df, tmp_path):
    """Cross-check the detector map against the gate rules (pandas mirror of the GX suite)."""
    corrupted, _ = _run(clean_df, tmp_path)
    settings = SimpleNamespace(freshness_threshold_days=180)

    assert all(result["success"] for result in _manual_expectation_results(clean_df))
    assert _freshness_payload(clean_df, settings)["is_fresh"]

    failed = {result["type"] for result in _manual_expectation_results(corrupted) if not result["success"]}
    assert failed == {"ExpectColumnValuesToBeUnique", "ExpectColumnValueLengthsToBeBetween"}
    assert not _freshness_payload(corrupted, settings)["is_fresh"]


def test_custom_config_changes_severity(clean_df, tmp_path):
    config = CorruptionConfig(drop_latest_ratio=0.5, truncated_title_length=3, stale_shift_days=30)
    corrupted, log = _run(clean_df, tmp_path, config)
    by_id = corrupted.drop_duplicates("paper_id").set_index("paper_id")

    assert _event(log, "drop_latest_records")["count"] == 5
    for paper_id in _event(log, "truncate_title")["paper_ids"]:
        assert len(by_id.at[paper_id, "title"]) == 3
    assert log["config"]["stale_shift_days"] == 30


@pytest.mark.parametrize(
    "overrides",
    [
        {"drop_latest_ratio": 0},
        {"group_ratio": 1.5},
        {"duplicate_ratio": -0.1},
        {"blank_summary_rows": 0},
        {"truncated_title_length": 8},
        {"stale_shift_days": 0},
        {"noise_suffix": "   "},
    ],
)
def test_invalid_config_is_rejected(overrides):
    with pytest.raises(ValueError):
        CorruptionConfig(**overrides)


def test_empty_dataframe_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        corrupt_clean_dataframe(pd.DataFrame(), tmp_path / "log.json")
