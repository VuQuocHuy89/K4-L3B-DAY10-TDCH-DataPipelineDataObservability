from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean
import os
import sys
import types
from typing import Any

from datasets import Dataset
import pandas as pd
from pydantic import BaseModel, Field

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json
from retrieval.agent import build_agent, run_agent_question
from retrieval.embeddings import MiniLMEmbeddings
from retrieval.index import LocalEmbeddingIndex
from retrieval.llm import build_llm
from retrieval.qa import answer_question


class JudgeVerdict(BaseModel):
    score: int = Field(ge=1, le=5)
    correct: bool
    reasoning: str


@dataclass(frozen=True)
class EvaluationBundle:
    summary: dict[str, Any]
    answers: list[dict[str, Any]]


def _reciprocal_rank(retrieved_doc_ids: list[str], relevant_doc_ids: list[str]) -> float:
    """Return the reciprocal rank of the first relevant retrieved document."""
    relevant = {str(doc_id) for doc_id in relevant_doc_ids}
    for rank, doc_id in enumerate(retrieved_doc_ids, start=1):
        if str(doc_id) in relevant:
            return 1.0 / rank
    return 0.0


def _average_precision(retrieved_doc_ids: list[str], relevant_doc_ids: list[str]) -> float:
    """Return average precision for a ranked list of retrieved documents."""
    relevant = {str(doc_id) for doc_id in relevant_doc_ids}
    if not relevant:
        return 0.0

    hits = 0
    precision_sum = 0.0
    matched: set[str] = set()
    for rank, doc_id in enumerate(retrieved_doc_ids, start=1):
        normalized_id = str(doc_id)
        if normalized_id in relevant and normalized_id not in matched:
            matched.add(normalized_id)
            hits += 1
            precision_sum += hits / rank
    return precision_sum / len(relevant)


def _token_f1(reference: str, prediction: str) -> float:
    ref_tokens = normalize_whitespace(reference).lower().split()
    pred_tokens = normalize_whitespace(prediction).lower().split()
    if not ref_tokens or not pred_tokens:
        return 0.0
    ref_set = set(ref_tokens)
    pred_set = set(pred_tokens)
    overlap = len(ref_set & pred_set)
    if overlap == 0:
        return 0.0
    precision = overlap / len(pred_set)
    recall = overlap / len(ref_set)
    return 2 * precision * recall / (precision + recall)


def _judge_answer(settings: Settings, question: str, reference: str, prediction: str) -> JudgeVerdict:
    prompt = f"""
Evaluate the model answer against the reference answer.

Question: {question}
Reference answer: {reference}
Model answer: {prediction}

Return:
- score from 1 to 5
- correct = true only when the answer is materially correct
- short reasoning
""".strip()
    try:
        llm = build_llm(settings=settings, temperature=0.0).with_structured_output(JudgeVerdict)
        return llm.invoke(prompt)
    except Exception:
        score = 5 if _token_f1(reference, prediction) >= 0.95 else 3 if _token_f1(reference, prediction) >= 0.5 else 1
        return JudgeVerdict(
            score=score,
            correct=score >= 3,
            reasoning="Fallback heuristic judge used because the LLM evaluator was unavailable.",
        )


def _run_ragas(settings: Settings, answers: list[dict[str, Any]]) -> dict[str, Any]:
    if os.getenv("RUN_RAGAS", "").lower() not in {"1", "true", "yes"}:
        return {
            "status": "skipped",
            "enabled": False,
            "message": "Set RUN_RAGAS=1 to enable the slower Ragas pass.",
            "scores": {},
        }
    try:
        # Ragas 0.3 imports this optional module during package import, while
        # langchain-community is not a direct project dependency.
        if "langchain_community.chat_models.vertexai" not in sys.modules:
            shim = types.ModuleType("langchain_community.chat_models.vertexai")
            shim.ChatVertexAI = type("ChatVertexAI", (), {})
            sys.modules["langchain_community.chat_models.vertexai"] = shim
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

        dataset = Dataset.from_dict(
            {
                "question": [item["question"] for item in answers],
                "answer": [item["answer"] for item in answers],
                "ground_truth": [item["ground_truth"] for item in answers],
                "contexts": [item["retrieved_contexts"] for item in answers],
            }
        )
        result = evaluate(
            dataset,
            metrics=[answer_relevancy, context_precision, context_recall, faithfulness],
            llm=build_llm(settings=settings, temperature=0.0),
            embeddings=MiniLMEmbeddings(settings.embedding_model),
            column_map={
                "user_input": "question",
                "response": "answer",
                "reference": "ground_truth",
                "retrieved_contexts": "contexts",
            },
            raise_exceptions=False,
            show_progress=False,
        )
        frame = result.to_pandas()
        metric_names = (
            "answer_relevancy",
            "context_precision",
            "context_recall",
            "faithfulness",
        )
        scores: dict[str, float | None] = {}
        for metric_name in metric_names:
            if metric_name not in frame.columns:
                scores[metric_name] = None
                continue
            values = pd.to_numeric(frame[metric_name], errors="coerce").dropna()
            scores[metric_name] = float(values.mean()) if not values.empty else None
        return {
            "status": "ok",
            "enabled": True,
            "samples": int(len(frame)),
            "scores": scores,
        }
    except Exception as exc:  # pragma: no cover
        return {
            "status": "error",
            "enabled": True,
            "scores": {},
            "error": f"Ragas evaluation failed: {exc}",
        }


def _agent_answers_path(answers_output_path) -> Path:
    path = Path(answers_output_path)
    stem = path.stem.removesuffix("_answers")
    return path.with_name(f"{stem}_agent_answers{path.suffix or '.json'}")


def _run_agent_evaluation(
    settings: Settings,
    index: LocalEmbeddingIndex,
    test_set: list[dict[str, Any]],
    answers_output_path,
) -> dict[str, Any]:
    """Optionally score the LangChain agent separately from the extractive QA path."""
    if os.getenv("RUN_AGENT_EVALUATION", "").strip().lower() not in {"1", "true", "yes"}:
        return {
            "status": "skipped",
            "enabled": False,
            "message": "Set RUN_AGENT_EVALUATION=1 to evaluate the LangChain agent.",
            "scores": {},
        }

    try:
        agent = build_agent(settings=settings, index=index)
    except Exception as exc:
        return {
            "status": "error",
            "enabled": True,
            "samples": 0,
            "error_type": type(exc).__name__,
            "message": "Agent initialization failed; check the configured provider and credentials.",
            "scores": {},
        }

    agent_answers: list[dict[str, Any]] = []
    for item in test_set:
        error_type = None
        try:
            prediction = run_agent_question(agent, item["question"])
        except Exception as exc:
            prediction = ""
            error_type = type(exc).__name__
            judge = JudgeVerdict(
                score=1,
                correct=False,
                reasoning=f"Agent invocation failed ({error_type}).",
            )
        else:
            judge = _judge_answer(settings, item["question"], item["ground_truth"], prediction)

        answer_record = {
            "id": item["id"],
            "question_type": item["question_type"],
            "question": item["question"],
            "ground_truth": item["ground_truth"],
            "answer": prediction,
            "token_f1": _token_f1(item["ground_truth"], prediction),
            "judge": judge.model_dump(),
        }
        if error_type:
            answer_record["agent_error_type"] = error_type
        agent_answers.append(answer_record)

    output_path = _agent_answers_path(answers_output_path)
    write_json(output_path, agent_answers)
    answered_samples = sum(bool(item["answer"].strip()) for item in agent_answers)
    score_count = len(agent_answers)
    scores = {
        "mean_token_f1": mean(item["token_f1"] for item in agent_answers) if score_count else 0.0,
        "judge_accuracy": (
            mean(1.0 if item["judge"]["correct"] else 0.0 for item in agent_answers)
            if score_count
            else 0.0
        ),
        "mean_judge_score": mean(item["judge"]["score"] for item in agent_answers) if score_count else 0.0,
    }
    status = "ok" if answered_samples == score_count else "partial" if answered_samples else "error"
    return {
        "status": status,
        "enabled": True,
        "samples": score_count,
        "answered_samples": answered_samples,
        "scores": scores,
        "answers_path": output_path.name,
    }


def evaluate_pipeline(
    settings: Settings,
    index: LocalEmbeddingIndex,
    test_set_path,
    metrics_output_path,
    answers_output_path,
) -> EvaluationBundle:
    test_set = read_json(test_set_path)
    answers: list[dict[str, Any]] = []

    for item in test_set:
        result = answer_question(item["question"], settings=settings, index=index)
        judge = _judge_answer(settings, item["question"], item["ground_truth"], result.answer)
        average_precision = _average_precision(
            result.retrieved_doc_ids,
            item["ground_truth_doc_ids"],
        )
        reciprocal_rank = _reciprocal_rank(
            result.retrieved_doc_ids,
            item["ground_truth_doc_ids"],
        )
        retrieval_hit = reciprocal_rank > 0.0
        answers.append(
            {
                "id": item["id"],
                "question_type": item["question_type"],
                "question": item["question"],
                "ground_truth": item["ground_truth"],
                "ground_truth_doc_ids": item["ground_truth_doc_ids"],
                "answer": result.answer,
                "retrieved_doc_ids": result.retrieved_doc_ids,
                "retrieved_contexts": result.retrieved_contexts,
                "retrieval_hit": retrieval_hit,
                "average_precision": average_precision,
                "reciprocal_rank": reciprocal_rank,
                "token_f1": _token_f1(item["ground_truth"], result.answer),
                "judge": judge.model_dump(),
            }
        )

    map_score = mean(item["average_precision"] for item in answers) if answers else 0.0
    mrr_score = mean(item["reciprocal_rank"] for item in answers) if answers else 0.0
    summary = {
        "samples": len(answers),
        "retrieval_hit_rate": mean(1.0 if item["retrieval_hit"] else 0.0 for item in answers),
        "map": map_score,
        "mrr": mrr_score,
        "mean_average_precision": map_score,
        "mean_reciprocal_rank": mrr_score,
        "mean_token_f1": mean(item["token_f1"] for item in answers),
        "judge_accuracy": mean(1.0 if item["judge"]["correct"] else 0.0 for item in answers),
        "mean_judge_score": mean(item["judge"]["score"] for item in answers),
    }
    summary["agent_evaluation"] = _run_agent_evaluation(
        settings,
        index,
        test_set,
        answers_output_path,
    )
    summary["ragas"] = _run_ragas(settings, answers)

    bundle = EvaluationBundle(summary=summary, answers=answers)
    write_json(metrics_output_path, summary)
    write_json(answers_output_path, answers)
    return bundle
