# Corruption and Idempotent Repair Report

The corruption flow starts from the same cleaned baseline on every run, records six controlled mutations in `data/results/corruption_log.json`, and reconstructs the repaired corpus from `data/raw/crossref_records.json`.

## Automated self-healing

- Triggered: **PASS**
- Reasons: **quality:ExpectColumnValuesToBeUnique, quality:ExpectColumnValueLengthsToBeBetween, quality:freshness**
- Repair source: **raw_snapshot**
- Repair log: `F:\UIT\AITC\Lab10\K4-L3B-DAY10-TDCH-DataPipelineDataObservability\data\results\repair_log.json`

## Three-state comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Retrieval Hit Rate | 100.0% | 60.0% | 100.0% |
| Mean Average Precision (MAP) | 100.0% | 53.3% | 100.0% |
| Mean Reciprocal Rank (MRR) | 100.0% | 53.3% | 100.0% |
| Mean Token F1 | 100.0% | 70.0% | 100.0% |
| LLM Judge Accuracy | 100.0% | 70.0% | 100.0% |
| Mean LLM Judge Score | 5.00 / 5 | 3.80 / 5 | 5.00 / 5 |
| Samples | 10 | 10 | 10 |
| GX + Freshness Gate | Baseline report (see phase 1) | FAIL | PASS |
| Freshness SLA | See baseline report | FAIL | PASS |
| RAGAS Status | skipped | skipped | skipped |
| RAGAS Answer Relevancy | N/A | N/A | N/A |
| RAGAS Context Precision | N/A | N/A | N/A |
| RAGAS Context Recall | N/A | N/A | N/A |
| RAGAS Faithfulness | N/A | N/A | N/A |

## Impact and recovery

- Mean Token F1 fell by 30.0% after corruption.
- Repair restored Mean Token F1 to the baseline value.
- Corrupted Quality Gate: **FAIL**; Freshness SLA: **FAIL**.
- Repaired Quality Gate: **PASS**; Freshness SLA: **PASS**.
- The three metric files and per-question answer files under `data/results/` contain the source measurements behind this report.
