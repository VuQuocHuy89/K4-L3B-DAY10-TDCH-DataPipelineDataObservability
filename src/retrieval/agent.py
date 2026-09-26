from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool

from core.config import Settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.llm import build_llm


def build_agent(settings: Settings, index: LocalEmbeddingIndex, top_k: int | None = None):
    default_top_k = top_k or settings.top_k

    @tool
    def semantic_search_papers(query: str, top_k: int = default_top_k) -> str:
        """Search the local paper corpus with embeddings and return the most relevant papers."""
        results = index.search(query, top_k=top_k)
        lines = []
        for result in results:
            lines.append(
                f"paper_id: {result.paper_id}\n"
                f"title: {result.title}\n"
                f"score: {result.score:.4f}\n"
                f"{result.content}"
            )
        return "\n\n".join(lines)

    @tool
    def lookup_paper(paper_id_or_title: str) -> str:
        """Look up a paper by exact paper_id or exact title from the local corpus."""
        record = index.lookup(paper_id_or_title)
        if not record:
            return "No exact paper match found."
        return (
            f"paper_id: {record['paper_id']}\n"
            f"title: {record['title']}\n"
            f"{record['content']}"
        )

    llm = build_llm(settings=settings, temperature=0.0)
    return create_agent(
        model=llm,
        tools=[semantic_search_papers, lookup_paper],
        system_prompt=(
            "You answer questions about the indexed scholarly paper corpus sourced from Crossref. "
            "Use tools before answering factual questions. "
            "If the indexed corpus does not support the answer, say so clearly."
        ),
        name="paper_corpus_agent",
    )


def run_agent_question(agent: Any, question: str) -> str:
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    messages = result.get("messages", [])
    if not messages:
        return ""
    final_message = messages[-1]
    if isinstance(final_message, dict):
        content = final_message.get("content", "")
    else:
        content = getattr(final_message, "content", final_message)

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = [
            block if isinstance(block, str) else block.get("text", "")
            for block in content
            if isinstance(block, str) or isinstance(block, dict)
        ]
        return "\n".join(part for part in text_parts if isinstance(part, str) and part)
    return str(content) if content is not None else ""
