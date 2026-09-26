from __future__ import annotations

import json

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    settings = load_settings()
    run_date = now_utc()

    records = fetch_source_records(settings)
    clean_df = build_clean_dataframe(records, run_date)
    if clean_df.empty:
        raise RuntimeError("Ingestion and cleaning produced no valid paper records.")

    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    if quality["engine"] != "great_expectations_1.x":
        raise RuntimeError(
            "Great Expectations 1.x could not run; the quality report contains a fallback diagnostic. "
            f"Install project dependencies and inspect {settings.paths.baseline_quality_report}."
        )
    if not quality["success"]:
        failed = [item["type"] for item in quality["expectations"] if not item.get("success")]
        raise RuntimeError(
            "Baseline Data Quality Gate failed; refusing to index the data. "
            f"Failed expectations: {', '.join(failed) or 'Freshness SLA'}. "
            f"See {settings.paths.baseline_quality_report}."
        )

    if not settings.paths.eval_testset.exists() or settings.refresh_test_set or settings.refresh_source:
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
    else:
        test_set = json.loads(settings.paths.eval_testset.read_text(encoding="utf-8"))
    if len(test_set) != 10:
        raise RuntimeError(f"Expected a 10-question evaluation set, found {len(test_set)} in {settings.paths.eval_testset}.")

    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    bundle = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    source_summary = {
        "configured_source": settings.source_api,
        "data_mode": "live API requested" if settings.refresh_source else "offline snapshot preferred",
        "raw_records_loaded": len(records),
        "clean_records_indexed": len(clean_df),
        "evaluation_questions": len(test_set),
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary,
        bundle.summary,
        quality,
        freshness,
    )

    print("Baseline pipeline completed.")
    print(json.dumps(bundle.summary, indent=2, ensure_ascii=False))
    print(f"Quality gate: {quality['success']} ({quality['engine']})")
    print(f"Freshness SLA: {freshness['is_fresh']} ({freshness['stale_rows']}/{freshness['total_rows']} stale)")
    print(f"Report: {settings.paths.baseline_report}")
