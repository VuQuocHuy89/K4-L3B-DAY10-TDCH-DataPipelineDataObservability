from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text


_SCORE_KEYS = (
    ("retrieval_hit_rate", "Retrieval Hit Rate"),
    ("map", "Mean Average Precision (MAP)"),
    ("mrr", "Mean Reciprocal Rank (MRR)"),
    ("mean_token_f1", "Mean Token F1"),
    ("judge_accuracy", "LLM Judge Accuracy"),
    ("mean_judge_score", "Mean LLM Judge Score"),
)
_RAGAS_KEYS = (
    ("answer_relevancy", "Answer Relevancy"),
    ("context_precision", "Context Precision"),
    ("context_recall", "Context Recall"),
    ("faithfulness", "Faithfulness"),
)


def _format_value(value: Any, key: str = "") -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, (int, float)):
        if key in {
            "retrieval_hit_rate",
            "map",
            "mrr",
            "mean_average_precision",
            "mean_reciprocal_rank",
            "mean_token_f1",
            "judge_accuracy",
            "answer_relevancy",
            "context_precision",
            "context_recall",
            "faithfulness",
            "stale_ratio",
        }:
            return f"{value:.1%}"
        if key == "mean_judge_score":
            return f"{value:.2f} / 5"
        return str(value) if isinstance(value, int) else f"{value:.4f}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _quality_status(quality: dict[str, Any]) -> str:
    engine = quality.get("engine", "unknown")
    status = "PASS" if quality.get("success") else "FAIL"
    if engine != "great_expectations_1.x":
        status += f" (engine: {engine})"
    return status


def _ragas_score(metrics: dict[str, Any], key: str) -> Any:
    ragas = metrics.get("ragas", {})
    if not isinstance(ragas, dict):
        return None
    scores = ragas.get("scores", {})
    return scores.get(key) if isinstance(scores, dict) else None


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    score_rows = "\n".join(
        f"| {label} | {_format_value(metrics.get(key), key)} |" for key, label in _SCORE_KEYS
    )
    expectations = quality.get("expectations", [])
    quality_rows = "\n".join(
        f"| {item.get('type', 'Expectation')} | {_format_value(item.get('success'))} |"
        for item in expectations
    ) or "| No expectation details | N/A |"
    source_rows = "\n".join(
        f"| {key.replace('_', ' ').title()} | {_format_value(value)} |" for key, value in source_summary.items()
    )

    content = f"""# Phase 1 — Baseline Pipeline Report

## Data source

| Item | Value |
| --- | --- |
{source_rows}

## Baseline evaluation

| Metric | Result |
| --- | ---: |
{score_rows}

Samples evaluated: **{_format_value(metrics.get('samples'))}**

The LLM judge may use its recorded heuristic fallback when the configured provider is unavailable. See `baseline_answers.json` for per-question judge reasoning.

## RAGAS evaluation

- Status: **{_format_value(metrics.get('ragas', {}).get('status') if isinstance(metrics.get('ragas'), dict) else None)}**
{chr(10).join(f"- {label}: **{_format_value(_ragas_score(metrics, key), key)}**" for key, label in _RAGAS_KEYS)}

## Data quality gate

Overall status: **{_quality_status(quality)}**<br>
Validation engine: `{_format_value(quality.get('engine'))}`; rows checked: **{_format_value(quality.get('row_count'))}**.

| Great Expectations check | Result |
| --- | --- |
{quality_rows}

## Freshness SLA

- Status: **{_format_value(freshness.get('is_fresh'))}**
- Latest / oldest publication: `{_format_value(freshness.get('latest_published'))}` / `{_format_value(freshness.get('oldest_published'))}`
- Stale records (`age_days > {freshness.get('threshold_days', 180)}): **{_format_value(freshness.get('stale_rows'))} / {_format_value(freshness.get('total_rows'))}** ({_format_value(freshness.get('stale_ratio'), 'stale_ratio')})
- SLA limit: no more than 25% stale records.

## Artifacts

See `data/results/baseline_metrics.json`, `data/results/baseline_answers.json`, `data/quality/baseline_quality_report.json`, and `data/quality/freshness_report.json` for machine-readable results.
"""
    write_text(Path(report_path), content)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    rows: list[str] = []
    for key, label in _SCORE_KEYS:
        rows.append(
            "| {} | {} | {} | {} |".format(
                label,
                _format_value(baseline_metrics.get(key), key),
                _format_value(corrupted_metrics.get(key), key),
                _format_value(repaired_metrics.get(key), key),
            )
        )
    rows.extend(
        [
            "| Samples | {} | {} | {} |".format(
                _format_value(baseline_metrics.get("samples")),
                _format_value(corrupted_metrics.get("samples")),
                _format_value(repaired_metrics.get("samples")),
            ),
            "| GX + Freshness Gate | {} | {} | {} |".format(
                "Baseline report (see phase 1)",
                _quality_status(corrupted_quality),
                _quality_status(repaired_quality),
            ),
            "| Freshness SLA | {} | {} | {} |".format(
                "See baseline report",
                _format_value(corrupted_freshness.get("is_fresh")),
                _format_value(repaired_freshness.get("is_fresh")),
            ),
            "| RAGAS Status | {} | {} | {} |".format(
                _format_value((baseline_metrics.get("ragas") or {}).get("status")),
                _format_value((corrupted_metrics.get("ragas") or {}).get("status")),
                _format_value((repaired_metrics.get("ragas") or {}).get("status")),
            ),
        ]
    )
    for key, label in _RAGAS_KEYS:
        rows.append(
            "| RAGAS {} | {} | {} | {} |".format(
                label,
                _format_value(_ragas_score(baseline_metrics, key), key),
                _format_value(_ragas_score(corrupted_metrics, key), key),
                _format_value(_ragas_score(repaired_metrics, key), key),
            )
        )

    baseline_f1 = float(baseline_metrics.get("mean_token_f1", 0.0) or 0.0)
    corrupted_f1 = float(corrupted_metrics.get("mean_token_f1", 0.0) or 0.0)
    repaired_f1 = float(repaired_metrics.get("mean_token_f1", 0.0) or 0.0)
    if corrupted_f1 < baseline_f1:
        corruption_summary = f"Mean Token F1 fell by {baseline_f1 - corrupted_f1:.1%} after corruption."
    else:
        corruption_summary = "Mean Token F1 did not fall in this run; inspect per-question results and retrieval behavior."
    repair_gap = abs(repaired_f1 - baseline_f1)
    if repair_gap < 1e-9:
        repair_summary = "Repair restored Mean Token F1 to the baseline value."
    else:
        repair_summary = f"Repaired Mean Token F1 differs from baseline by {repair_gap:.1%}; inspect the artifacts for remaining variation."

    content = f"""# Corruption and Idempotent Repair Report

The corruption flow starts from the same cleaned baseline on every run, records six controlled mutations in `data/results/corruption_log.json`, and reconstructs the repaired corpus from `data/raw/crossref_records.json`.

## Three-state comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
{chr(10).join(rows)}

## Impact and recovery

- {corruption_summary}
- {repair_summary}
- Corrupted Quality Gate: **{_quality_status(corrupted_quality)}**; Freshness SLA: **{_format_value(corrupted_freshness.get('is_fresh'))}**.
- Repaired Quality Gate: **{_quality_status(repaired_quality)}**; Freshness SLA: **{_format_value(repaired_freshness.get('is_fresh'))}**.
- The three metric files and per-question answer files under `data/results/` contain the source measurements behind this report.
"""
    write_text(Path(report_path), content)
