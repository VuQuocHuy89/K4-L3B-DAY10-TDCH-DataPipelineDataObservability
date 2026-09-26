from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _load_clean_frame(path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Clean dataset not found at {path}; run script/run_phase1.py first.")
    frame = pd.read_json(path)
    if frame.empty:
        raise RuntimeError(f"Clean dataset at {path} is empty; run script/run_phase1.py first.")
    return frame


def _print_comparison(baseline: dict, corrupted: dict, repaired: dict) -> None:
    rows = [
        ("Hit Rate", "retrieval_hit_rate"),
        ("MAP", "map"),
        ("MRR", "mrr"),
        ("Token F1", "mean_token_f1"),
        ("LLM Judge Accuracy", "judge_accuracy"),
    ]
    print("\nBaseline vs Corrupted vs Repaired")
    print(f"{'Metric':<24} {'Baseline':>12} {'Corrupted':>12} {'Repaired':>12}")
    for label, key in rows:
        values = [float(metrics.get(key, 0.0) or 0.0) for metrics in (baseline, corrupted, repaired)]
        print(f"{label:<24} {values[0]:>11.1%} {values[1]:>11.1%} {values[2]:>11.1%}")

    print("\nRAGAS status and scores")
    ragas_keys = ("answer_relevancy", "context_precision", "context_recall", "faithfulness")
    statuses = [str((metrics.get("ragas") or {}).get("status", "unknown")) for metrics in (baseline, corrupted, repaired)]
    print(f"{'Status':<24} {statuses[0]:>12} {statuses[1]:>12} {statuses[2]:>12}")
    for key in ragas_keys:
        values = [
            ((metrics.get("ragas") or {}).get("scores", {}) or {}).get(key)
            for metrics in (baseline, corrupted, repaired)
        ]
        formatted = ["N/A" if value is None else f"{float(value):.1%}" for value in values]
        print(f"RAGAS {key:<17} {formatted[0]:>12} {formatted[1]:>12} {formatted[2]:>12}")


def main() -> None:
    settings = load_settings()
    if not settings.paths.baseline_metrics.exists():
        raise FileNotFoundError("Baseline metrics are missing; run script/run_phase1.py before the corruption flow.")
    if not settings.paths.eval_testset.exists():
        raise FileNotFoundError("Evaluation set is missing; run script/run_phase1.py before the corruption flow.")

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_df = _load_clean_frame(settings.paths.clean_json)

    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    # Corrupted rows intentionally pass through the checks so the alert can be saved,
    # then indexed to measure downstream RAG degradation.
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(corrupted_df, settings, report_path=None)
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        settings.paths.corrupted_embeddings_json,
    )
    corrupted_bundle = evaluate_pipeline(
        settings,
        corrupted_index,
        settings.paths.eval_testset,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )

    # Repair always starts from the preserved raw records, never the corrupted frame.
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    if repaired_df.empty:
        raise RuntimeError("Repair from the raw backup produced no valid records.")
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))

    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(repaired_df, settings, report_path=None)
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        settings.paths.repaired_embeddings_json,
    )
    repaired_bundle = evaluate_pipeline(
        settings,
        repaired_index,
        settings.paths.eval_testset,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )

    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_bundle.summary,
        repaired_bundle.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    _print_comparison(baseline_metrics, corrupted_bundle.summary, repaired_bundle.summary)
    print(f"Corruption log: {settings.paths.corruption_log}")
    print(f"Comparison report: {settings.paths.comparison_report}")
