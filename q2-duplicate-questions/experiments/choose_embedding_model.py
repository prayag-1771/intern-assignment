"""Choose the local embedding model by scoring each one on our 50-question answer key.

For every answer-key question a model finds the most similar of the ten corpus
questions and gives that pair a score. Two things matter:

  Nearest right   For a question that has a partner in the corpus (a copy, a
                  rewording, a variant or a "needs review" case), is the nearest
                  corpus question that partner?

  Judge workload  The search stage may skip the LLM judge only for questions that
                  score below a cut-off. The cut-off must sit below every question
                  that has a partner, or a duplicate slips past unseen. So: with
                  the cut-off at the lowest partnered score, how many of the
                  'different' questions still go to the judge?

Plain copies are caught by text matching before this stage, so the second
measure leaves them out.

Run from q2-duplicate-questions/:
    python -m experiments.choose_embedding_model
"""

from __future__ import annotations

import gc
import json
import time
from pathlib import Path

import numpy as np

from experiments.compare_embeddings import EQUIVALENCE_INSTRUCTION, TfidfBaseline
from qbank.config import api_key
from qbank.datasets import duplicate_groups, load_answer_key, load_corpus
from qbank.embedders import GeminiEmbedder, LocalEmbedder

RESULTS_PATH = Path(__file__).resolve().parent / "results" / "embedding_model_choice.json"

# (name shown in results, Hugging Face model id, instruction placed before each question or None)
LOCAL_MODELS: list[tuple[str, str, str | None]] = [
    ("all-MiniLM-L6-v2", "sentence-transformers/all-MiniLM-L6-v2", None),
    ("paraphrase-MiniLM-L6-v2", "sentence-transformers/paraphrase-MiniLM-L6-v2", None),
    ("bge-small-en-v1.5", "BAAI/bge-small-en-v1.5", None),
    ("quora-distilbert-base", "sentence-transformers/quora-distilbert-base", None),
    ("all-mpnet-base-v2", "sentence-transformers/all-mpnet-base-v2", None),
    ("paraphrase-mpnet-base-v2", "sentence-transformers/paraphrase-mpnet-base-v2", None),
    ("bge-base-en-v1.5", "BAAI/bge-base-en-v1.5", None),
    ("gte-modernbert-base", "Alibaba-NLP/gte-modernbert-base", None),
    ("Qwen3-Embedding-0.6B", "Qwen/Qwen3-Embedding-0.6B", None),
    ("Qwen3-Embedding-0.6B + instruction", "Qwen/Qwen3-Embedding-0.6B", EQUIVALENCE_INSTRUCTION),
]

# A reviewer may have no GPU, so speed is also measured on the CPU, on this many questions.
CPU_TIMING_QUESTIONS = 20


def evaluate(similarity: np.ndarray, bank: list[dict], candidates: list[dict]) -> dict:
    """Score one model. `similarity` has a row per candidate and a column per corpus question."""
    group = duplicate_groups(bank)
    bank_ids = [q["id"] for q in bank]

    rows = []
    for scores, candidate in zip(similarity, candidates):
        nearest = int(np.argmax(scores))
        expected = {group[qid] for qid in candidate["of"]}
        # The judge is shown the nearest few questions, so the partner need not be first.
        # Several corpus entries can be copies of one question; each question is counted once.
        best_of_question: dict[str, float] = {}
        for qid, score in zip(bank_ids, scores):
            best_of_question[group[qid]] = max(best_of_question.get(group[qid], -1.0), float(score))
        nearest_three = sorted(best_of_question, key=best_of_question.get, reverse=True)[:3]
        rows.append(
            {
                "id": candidate["id"],
                "label": candidate["label"],
                "nearest": bank_ids[nearest],
                "score": round(float(scores[nearest]), 4),
                "nearest_right": group[bank_ids[nearest]] in expected,
                "partner_in_nearest_three": bool(expected & set(nearest_three)),
            }
        )

    partnered = [r for r in rows if r["label"] != "different"]
    # Plain copies never reach this stage, so the cut-off is worked out on the rest.
    reworded = [r for r in partnered if r["label"] != "exact_duplicate"]
    different = [r for r in rows if r["label"] == "different"]

    lowest_partnered = min(reworded, key=lambda r: r["score"])
    highest_different = max(different, key=lambda r: r["score"])
    sent_to_judge = [r for r in different if r["score"] >= lowest_partnered["score"]]
    # Chance that a partnered question outscores a different one (1.0 is perfect, 0.5 is a coin toss).
    wins = sum((p["score"] > d["score"]) + 0.5 * (p["score"] == d["score"]) for p in reworded for d in different)

    return {
        "nearest_right": sum(r["nearest_right"] for r in partnered),
        "partnered": len(partnered),
        "nearest_wrong_ids": [r["id"] for r in partnered if not r["nearest_right"]],
        "partner_in_nearest_three": sum(r["partner_in_nearest_three"] for r in partnered),
        "missed_by_search_ids": [r["id"] for r in partnered if not r["partner_in_nearest_three"]],
        "lowest_partnered_score": lowest_partnered["score"],
        "lowest_partnered_id": lowest_partnered["id"],
        "highest_different_score": highest_different["score"],
        "highest_different_id": highest_different["id"],
        "different_sent_to_judge": len(sent_to_judge),
        "different_total": len(different),
        "ranking_quality": round(wins / (len(reworded) * len(different)), 4),
        "candidates": rows,
    }


def _free_gpu_memory() -> None:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def run_local(model_id: str, prompt: str | None, bank_texts: list[str], candidate_texts: list[str]) -> tuple[np.ndarray, dict]:
    embedder = LocalEmbedder(model_id, prompt=prompt)
    bank_vectors = embedder.embed(bank_texts)
    similarity = embedder.embed(candidate_texts) @ bank_vectors.T
    details = {
        "kind": "local",
        "parameters_millions": round(embedder.parameter_count / 1e6, 1),
        "dimensions": int(bank_vectors.shape[1]),
        "device": embedder.device,
    }
    del embedder
    _free_gpu_memory()

    cpu_embedder = LocalEmbedder(model_id, prompt=prompt, device="cpu")
    sample = (bank_texts + candidate_texts)[:CPU_TIMING_QUESTIONS]
    cpu_embedder.embed(sample[:1])  # first call includes one-off start-up cost; do not time it
    started = time.perf_counter()
    cpu_embedder.embed(sample)
    details["cpu_ms_per_question"] = round(1000 * (time.perf_counter() - started) / len(sample), 1)
    del cpu_embedder
    _free_gpu_memory()
    return similarity, details


def main() -> None:
    bank = load_corpus()
    candidates = load_answer_key()
    bank_texts = [q["text"] for q in bank]
    candidate_texts = [c["text"] for c in candidates]

    # Options scored in an earlier run are kept, so a model that downloads later can be added
    # without repeating the slow ones. Delete the results file to score everything afresh.
    results: dict[str, dict] = {}
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH, encoding="utf-8") as handle:
            saved = json.load(handle)["options"]
        results = {name: r for name, r in saved.items() if "partner_in_nearest_three" in r}
    failures: dict[str, str] = {}  # not saved: a model that could not be loaded is simply tried again next run

    def record(name: str, similarity: np.ndarray, details: dict) -> None:
        results[name] = {**details, **evaluate(similarity, bank, candidates)}
        print(f"{name}: done", flush=True)
        # Saved after every option so a slow download later on does not lose earlier results.
        RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(RESULTS_PATH, "w", encoding="utf-8") as handle:
            json.dump({"options": results}, handle, indent=2)

    def attempt(name: str, run) -> None:
        if name in results:
            print(f"{name}: kept from an earlier run", flush=True)
            return
        try:
            record(name, *run())
        except Exception as error:  # a failed download should not lose the other results
            failures[name] = f"{type(error).__name__}: {error}"
            print(f"{name}: FAILED ({failures[name][:120]})", flush=True)

    def tfidf() -> tuple[np.ndarray, dict]:
        vectors = TfidfBaseline("TF-IDF, words", analyzer="word", ngram_range=(1, 2)).embed(bank_texts + candidate_texts)
        return vectors[len(bank_texts):] @ vectors[: len(bank_texts)].T, {"kind": "conventional"}

    def gemini() -> tuple[np.ndarray, dict]:
        embedder = GeminiEmbedder("gemini-embedding-001")
        return embedder.embed(candidate_texts) @ embedder.embed(bank_texts).T, {"kind": "online"}

    attempt("TF-IDF, words", tfidf)
    for name, model_id, prompt in LOCAL_MODELS:
        attempt(name, lambda: run_local(model_id, prompt, bank_texts, candidate_texts))
    if api_key("GEMINI_API_KEY"):
        attempt("gemini-embedding-001", gemini)

    print(f"\n{'option':<38}{'params M':>9}{'nearest right':>15}{'in top 3':>10}{'lowest partner':>16}{'highest diff':>14}{'to judge':>10}{'ranking':>9}{'cpu ms/q':>10}")
    for name, r in results.items():
        params = f"{r['parameters_millions']:.0f}" if "parameters_millions" in r else "-"
        cpu = f"{r['cpu_ms_per_question']:.0f}" if "cpu_ms_per_question" in r else "-"
        print(
            f"{name:<38}{params:>9}{str(r['nearest_right']) + '/' + str(r['partnered']):>15}"
            f"{str(r['partner_in_nearest_three']) + '/' + str(r['partnered']):>10}"
            f"{r['lowest_partnered_score']:>9.2f} {r['lowest_partnered_id']:<6}"
            f"{r['highest_different_score']:>7.2f} {r['highest_different_id']:<6}"
            f"{str(r['different_sent_to_judge']) + '/' + str(r['different_total']):>10}"
            f"{r['ranking_quality']:>9.2f}{cpu:>10}"
        )


if __name__ == "__main__":
    main()
