# Phase 1 — Baseline Pipeline Report

## Data source

| Item | Value |
| --- | --- |
| Configured Source | Crossref REST API |
| Data Mode | offline snapshot preferred |
| Raw Records Loaded | 24 |
| Clean Records Indexed | 24 |
| Evaluation Questions | 10 |
| Auto Repair Triggered | FAIL |
| Auto Repair Source | not_needed |

## Baseline evaluation

| Metric | Result |
| --- | ---: |
| Retrieval Hit Rate | 100.0% |
| Mean Average Precision (MAP) | 100.0% |
| Mean Reciprocal Rank (MRR) | 100.0% |
| Mean Token F1 | 100.0% |
| LLM Judge Accuracy | 100.0% |
| Mean LLM Judge Score | 5.00 / 5 |

Samples evaluated: **10**

The LLM judge may use its recorded heuristic fallback when the configured provider is unavailable. See `baseline_answers.json` for per-question judge reasoning.

## RAGAS evaluation

- Status: **skipped**
- Answer Relevancy: **N/A**
- Context Precision: **N/A**
- Context Recall: **N/A**
- Faithfulness: **N/A**

## Data quality gate

Overall status: **PASS**<br>
Validation engine: `great_expectations_1.x`; rows checked: **24**.

| Great Expectations check | Result |
| --- | --- |
| ExpectTableRowCountToBeBetween | PASS |
| ExpectColumnValuesToNotBeNull | PASS |
| ExpectColumnValuesToNotBeNull | PASS |
| ExpectColumnValuesToNotBeNull | PASS |
| ExpectColumnValuesToBeUnique | PASS |
| ExpectColumnValueLengthsToBeBetween | PASS |

## Freshness SLA

- Status: **PASS**
- Latest / oldest publication: `2026-07-22` / `2026-03-28`
- Stale records (`age_days > 180): **1 / 24** (4.2%)
- SLA limit: no more than 25% stale records.

## Artifacts

See `data/results/baseline_metrics.json`, `data/results/baseline_answers.json`, `data/quality/baseline_quality_report.json`, and `data/quality/freshness_report.json` for machine-readable results.
