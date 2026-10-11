"""Loads the assignment's ten questions and our own labelled answer key."""

from __future__ import annotations

import json

from .config import DATA_DIR

_DUPLICATE_KINDS = ("semantic_duplicate", "exact_duplicate")


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as handle:
        return json.load(handle)


def load_corpus() -> list[dict]:
    """The ten assignment questions with their expected labels."""
    return _load("corpus.json")["questions"]


def load_answer_key() -> list[dict]:
    """Our 50 labelled candidate questions, each judged against the corpus."""
    return _load("labelled_candidates.json")["candidates"]


def duplicate_groups(questions: list[dict]) -> dict[str, str]:
    """Map each corpus question id to the id of the question it ultimately repeats.

    Q2, Q3, Q4 and Q10 all map to Q1; a question that repeats nothing maps to itself.
    """
    by_id = {q["id"]: q for q in questions}

    def root(qid: str) -> str:
        while by_id[qid]["kind"] in _DUPLICATE_KINDS:
            qid = by_id[qid]["relates_to"]
        return qid

    return {qid: root(qid) for qid in by_id}
