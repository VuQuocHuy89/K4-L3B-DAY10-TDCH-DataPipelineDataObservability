from __future__ import annotations

from dataclasses import dataclass
import re

from core.config import Settings
from core.utils import first_sentence
from retrieval.index import LocalEmbeddingIndex, SearchResult


@dataclass(frozen=True)
class AnswerCandidate:
    paper_id: str
    title: str
    score: float
    answer: str
    context: str
    metadata: dict


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    retrieved_doc_ids: list[str]
    retrieved_contexts: list[str]
    retrieved_titles: list[str]
    candidates: list[AnswerCandidate]


def _retrieved_results(question: str, index: LocalEmbeddingIndex, top_k: int | None, settings: Settings) -> list[SearchResult]:
    title_match = re.search(r"'([^']+)'", question)
    exact = index.lookup(title_match.group(1)) if title_match else None
    retrieved = index.search(question, top_k=top_k)
    if exact:
        exact_result = SearchResult(
            paper_id=exact["paper_id"],
            title=exact["title"],
            score=1.0,
            content=exact["content"],
            metadata=exact["metadata"],
        )
        retrieved = [exact_result] + [item for item in retrieved if item.paper_id != exact_result.paper_id]
    return retrieved[: (top_k or settings.top_k)]


def _extract_answer(question: str, top_result: SearchResult) -> str:
    lowered = question.lower()
    metadata = top_result.metadata
    if "who authored" in lowered or "list the authors" in lowered:
        return metadata["authors_joined"]
    if "when was" in lowered or "publication date" in lowered or "published on" in lowered:
        return metadata["published"]
    if "what categories" in lowered:
        return metadata["categories_joined"]
    return first_sentence(metadata["summary"])


def answer_question(question: str, settings: Settings, index: LocalEmbeddingIndex, top_k: int | None = None) -> AnswerResult:
    retrieved = _retrieved_results(question, index, top_k, settings)
    candidates = [
        AnswerCandidate(
            paper_id=item.paper_id,
            title=item.title,
            score=item.score,
            answer=_extract_answer(question, item),
            context=item.content,
            metadata=item.metadata,
        )
        for item in retrieved
    ]
    if not candidates:
        answer = "I don't know from the indexed corpus."
    else:
        answer = candidates[0].answer
    return AnswerResult(
        question=question,
        answer=answer,
        retrieved_doc_ids=[item.paper_id for item in candidates],
        retrieved_contexts=[item.context for item in candidates],
        retrieved_titles=[item.title for item in candidates],
        candidates=candidates,
    )
