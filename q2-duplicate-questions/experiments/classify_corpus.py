"""Classify the assignment's ten questions the way the assignment asks, and compare with its labels.

The questions are taken in order, as if the bank were being built one question at a
time: each one is checked against all the questions before it, then added to the
bank whatever its label (this is an audit of an existing collection, so nothing is
removed). That is what makes Q10 an exact duplicate of Q2 rather than of Q1.

Run from q2-duplicate-questions/:
    python -m experiments.classify_corpus                       # the default judge
    python -m experiments.classify_corpus groq openai/gpt-oss-120b
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from qbank.datasets import duplicate_groups, load_corpus
from qbank.detector import DuplicateDetector
from qbank.embedders import LocalEmbedder
from qbank.judge import Judge
from qbank.llm import ChatModel
from qbank.search import QuestionIndex

RESULTS_DIR = Path(__file__).resolve().parent / "results"
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"  # decision D10
DEFAULT_JUDGE = ("gemini", "gemini-3.5-flash-lite")  # replaced once the judge is decided

# The assignment's wording for each kind, and the detector label that means the same thing.
EXPECTED_LABEL = {
    "original": "different",
    "semantic_duplicate": "semantic_duplicate",
    "exact_duplicate": "exact_duplicate",
    "different": "different",
    "ambiguous": "needs_review",
}


def agrees(question: dict, label: str, matches: tuple[str, ...], group: dict[str, str]) -> bool:
    """True when the detector's label is the assignment's, and it names a question in the right group."""
    if label != EXPECTED_LABEL[question["kind"]]:
        return False
    if question["relates_to"] is None:
        return True
    return group[question["relates_to"]] in {group[m] for m in matches}


def main() -> None:
    provider, model = sys.argv[1:3] if len(sys.argv) >= 3 else DEFAULT_JUDGE
    corpus = load_corpus()
    group = duplicate_groups(corpus)

    index = QuestionIndex(LocalEmbedder(EMBEDDING_MODEL))
    detector = DuplicateDetector(index, Judge(ChatModel(provider, model)))

    rows = []
    for question in corpus:
        detection = detector.check(question["text"])
        index.add([(question["id"], question["text"])])
        rows.append(
            {
                "id": question["id"],
                "text": question["text"],
                "assignment_says": question["expected"],
                "detector_says": detection.label,
                "matches": list(detection.matches),
                "method": detection.method,
                "reason": detection.reason,
                "agrees": agrees(question, detection.label, detection.matches, group),
            }
        )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"corpus_classification__{provider}__{model.replace('/', '__')}.json"
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"judge": f"{provider}/{model}", "embedding_model": EMBEDDING_MODEL, "questions": rows}, handle, indent=2, ensure_ascii=False)

    for row in rows:
        mark = "ok " if row["agrees"] else "XX "
        named = ",".join(row["matches"]) or "-"
        print(f"{mark}{row['id']:<4}{row['detector_says']:<19}{named:<16}assignment: {row['assignment_says']}")
    print(f"\n{sum(r['agrees'] for r in rows)}/{len(rows)} agree with the assignment ({provider}/{model}).")


if __name__ == "__main__":
    main()
