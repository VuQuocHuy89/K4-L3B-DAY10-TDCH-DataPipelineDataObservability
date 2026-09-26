from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a deterministic 10-question benchmark covering four QA intents."""
    if df.empty:
        raise ValueError("Cannot build an evaluation set from an empty dataframe.")
    required = {"paper_id", "title", "summary", "authors_joined", "published", "categories_joined"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Clean dataframe is missing test-set fields: {', '.join(sorted(missing))}.")

    ordered = df.sort_values(["paper_id"], kind="stable").head(10)
    if len(ordered) < 4:
        raise ValueError("At least four valid papers are required to cover all evaluation question types.")

    question_types = ("summary", "authors", "date", "categories")
    items: list[dict[str, Any]] = []
    for index, row in enumerate(ordered.to_dict(orient="records")):
        question_type = question_types[index % len(question_types)]
        title = str(row["title"]).strip()
        if question_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(str(row["summary"]))
        elif question_type == "authors":
            question = f"Who authored the paper '{title}'?"
            ground_truth = str(row["authors_joined"]).strip()
        elif question_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = str(row["published"]).strip()
        else:
            question = f"What categories describe the paper '{title}'?"
            ground_truth = str(row["categories_joined"]).strip()

        if not ground_truth:
            raise ValueError(f"Paper {row['paper_id']} has no ground truth for question type {question_type}.")
        items.append(
            {
                "id": f"eval_{index + 1:03d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [str(row["paper_id"])],
            }
        )

    output = Path(output_path)
    write_json(output, items)
    return items
