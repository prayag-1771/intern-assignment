"""Compare ways of turning questions into vectors, using the ten assignment questions.

The assignment's expected labels split every pair of questions into three kinds:

  duplicate  both questions are in the Q1 group (Q1, Q2, Q3, Q4, Q10)
  different  the two questions test different things
  ambiguous  Q8 against the Q1 group

A good option scores every duplicate pair above every different pair. The gap
between the lowest duplicate and the highest different pair is the room a
cut-off has to sit in: the wider, the safer.

Run from q2-duplicate-questions/:
    python -m experiments.compare_embeddings
"""

from __future__ import annotations

import itertools
import json
import time
from pathlib import Path
from typing import Callable

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from qbank.config import DATA_DIR, api_key
from qbank.embedders import Embedder, GeminiEmbedder, LocalEmbedder

RESULTS_PATH = Path(__file__).resolve().parent / "results" / "embedding_comparison.json"

# Instruction-tuned models accept a one-line description of the task. For a symmetric
# comparison (question against question) it goes in front of both texts.
EQUIVALENCE_INSTRUCTION = (
    "Instruct: Given a question, retrieve questions that are semantically equivalent "
    "to the given question\nQuery:"
)


class TfidfBaseline:
    """Word-count vectors (TF-IDF): the conventional, pre-transformer way to compare texts."""

    device = "cpu"

    def __init__(self, name: str, **vectorizer_options):
        self.name = name
        self._options = vectorizer_options

    def embed(self, texts):
        # TfidfVectorizer scales each row to length 1 by default, like the other embedders.
        return TfidfVectorizer(**self._options).fit_transform(list(texts)).toarray().astype(np.float32)


def options() -> list[tuple[str, Callable[[], Embedder]]]:
    """Each option is built only when its turn comes, so only one model is in memory at a time."""
    listed: list[tuple[str, Callable[[], Embedder]]] = [
        ("TF-IDF, words", lambda: TfidfBaseline("TF-IDF, words", analyzer="word", ngram_range=(1, 2))),
        ("TF-IDF, character n-grams", lambda: TfidfBaseline("TF-IDF, character n-grams", analyzer="char_wb", ngram_range=(3, 5))),
        ("all-MiniLM-L6-v2", lambda: LocalEmbedder("sentence-transformers/all-MiniLM-L6-v2")),
        ("all-mpnet-base-v2", lambda: LocalEmbedder("sentence-transformers/all-mpnet-base-v2")),
        ("Qwen3-Embedding-0.6B", lambda: LocalEmbedder("Qwen/Qwen3-Embedding-0.6B")),
        ("Qwen3-Embedding-0.6B + instruction", lambda: LocalEmbedder("Qwen/Qwen3-Embedding-0.6B", prompt=EQUIVALENCE_INSTRUCTION)),
    ]
    if api_key("GEMINI_API_KEY"):
        listed.append(("gemini-embedding-001", lambda: GeminiEmbedder("gemini-embedding-001")))
    return listed


def load_questions() -> list[dict]:
    with open(DATA_DIR / "corpus.json", encoding="utf-8") as handle:
        return json.load(handle)["questions"]


def pair_kinds(questions: list[dict]) -> dict[tuple[str, str], str]:
    """Label every pair of question ids as duplicate, different or ambiguous."""
    by_id = {q["id"]: q for q in questions}

    def group(qid: str) -> str:
        # Follow "duplicate of" links to the question a duplicate ultimately repeats.
        while by_id[qid]["kind"] in ("semantic_duplicate", "exact_duplicate"):
            qid = by_id[qid]["relates_to"]
        return qid

    kinds = {}
    for a, b in itertools.combinations(by_id, 2):
        ambiguous = [q for q in (by_id[a], by_id[b]) if q["kind"] == "ambiguous"]
        if ambiguous:
            other = b if ambiguous[0]["id"] == a else a
            # Only the pairs with the group it is ambiguous against are of interest.
            if group(other) == group(ambiguous[0]["relates_to"]):
                kinds[(a, b)] = "ambiguous"
        elif group(a) == group(b):
            kinds[(a, b)] = "duplicate"
        else:
            kinds[(a, b)] = "different"
    return kinds


def summarise(similarity: np.ndarray, ids: list[str], kinds: dict[tuple[str, str], str]) -> dict:
    row = {qid: i for i, qid in enumerate(ids)}
    scored = {kind: [] for kind in ("duplicate", "different", "ambiguous")}
    for (a, b), kind in kinds.items():
        scored[kind].append((float(similarity[row[a], row[b]]), a, b))

    lowest_duplicate = min(scored["duplicate"])
    highest_different = max(scored["different"])
    ambiguous_scores = [score for score, _, _ in scored["ambiguous"]]
    return {
        "lowest_duplicate": round(lowest_duplicate[0], 4),
        "lowest_duplicate_pair": list(lowest_duplicate[1:]),
        "highest_different": round(highest_different[0], 4),
        "highest_different_pair": list(highest_different[1:]),
        "gap": round(lowest_duplicate[0] - highest_different[0], 4),
        "ambiguous_low": round(min(ambiguous_scores), 4),
        "ambiguous_high": round(max(ambiguous_scores), 4),
        "q6_q7": round(float(similarity[row["Q6"], row["Q7"]]), 4),
    }


def run_option(build: Callable[[], Embedder], texts: list[str]) -> tuple[np.ndarray, dict]:
    embedder = build()
    embedder.embed(texts[:1])  # first call includes one-off start-up cost; do not time it
    started = time.perf_counter()
    vectors = embedder.embed(texts)
    seconds = time.perf_counter() - started
    details = {
        "dimensions": int(vectors.shape[1]),
        "device": getattr(embedder, "device", "cpu"),
        "seconds_for_ten_questions": round(seconds, 3),
    }
    return vectors @ vectors.T, details


def main() -> None:
    questions = load_questions()
    ids = [q["id"] for q in questions]
    texts = [q["text"] for q in questions]
    kinds = pair_kinds(questions)

    results = {}
    for name, build in options():
        try:
            similarity, details = run_option(build, texts)
        except Exception as error:  # a failed download should not lose the other results
            results[name] = {"error": f"{type(error).__name__}: {error}"}
            print(f"{name}: FAILED ({type(error).__name__}: {error})", flush=True)
            continue
        results[name] = {**details, **summarise(similarity, ids, kinds), "similarity": np.round(similarity, 4).tolist()}
        print(f"{name}: done", flush=True)

        # Saved after every option so a slow download later on does not lose earlier results.
        RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(RESULTS_PATH, "w", encoding="utf-8") as handle:
            json.dump({"question_ids": ids, "options": results}, handle, indent=2)

    header = f"{'option':<38}{'dims':>6}{'device':>8}{'low dup':>9}{'high diff':>11}{'gap':>8}{'Q8 range':>14}{'Q6-Q7':>8}{'sec':>8}"
    print("\n" + header)
    for name, r in results.items():
        if "error" in r:
            print(f"{name:<38}  failed: {r['error'][:80]}")
            continue
        q8_range = f"{r['ambiguous_low']:.2f}-{r['ambiguous_high']:.2f}"
        print(
            f"{name:<38}{r['dimensions']:>6}{r['device']:>8}{r['lowest_duplicate']:>9.2f}"
            f"{r['highest_different']:>11.2f}{r['gap']:>8.2f}{q8_range:>14}{r['q6_q7']:>8.2f}"
            f"{r['seconds_for_ten_questions']:>8.2f}"
        )


if __name__ == "__main__":
    main()
