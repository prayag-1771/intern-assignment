"""Choose the judge LLM by running each candidate on our 50-question answer key.

The search stage runs once: exact copies are caught by text, and for every other
question the five nearest assignment questions are found with the chosen embedding
model (D10). Every candidate LLM then judges exactly the same inputs, so the
comparison is fair.

Each answer is sorted by what it would do in practice:

  correct               the right label, and the right existing question named
  copy let in           a duplicate or variant judged "different": it enters the bank
  new question blocked  a "different" question judged a duplicate or variant: it is lost
  unclear decided       a "needs review" case decided without a person
  wrong question named  the right label, but it names the wrong existing question
  sent to a person      a clear case sent to review: safe, but costs a person's time
  wrong kind of block   a duplicate called a variant or the reverse: blocked either way
  no answer             no usable reply: held for a person (decision D9)

Replies are cached in data/llm_cache/, so a second run costs nothing and needs no key.

Run from q2-duplicate-questions/:
    python -m experiments.choose_judge_model
"""

from __future__ import annotations

import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from qbank.datasets import duplicate_groups, load_answer_key, load_corpus
from qbank.detector import SHOWN_TO_JUDGE
from qbank.embedders import LocalEmbedder
from qbank.judge import Judge, Verdict
from qbank.llm import ChatModel
from qbank.search import QuestionIndex

RESULTS_PATH = Path(__file__).resolve().parent / "results" / "judge_model_choice.json"
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"  # decision D10

CANDIDATE_JUDGES = [
    ("groq", "openai/gpt-oss-120b"),
    ("groq", "openai/gpt-oss-20b"),
    ("groq", "qwen/qwen3.8-27b"),
    ("gemini", "gemini-3.8-flash"),
    ("gemini", "gemini-3.5-flash-lite"),
]

BLOCKING = {"semantic_duplicate", "variant"}
OUTCOMES = [
    "correct",
    "copy let in",
    "new question blocked",
    "unclear decided",
    "wrong question named",
    "sent to a person",
    "wrong kind of block",
    "no answer",
]


def outcome(expected: str, verdict: Verdict, expected_groups: set[str], named_groups: set[str]) -> str:
    """Sort one judge answer into the categories described at the top of this file."""
    given = verdict.label
    if not verdict.judged:
        return "no answer"
    if given == expected:
        if expected == "different" or expected_groups <= named_groups:
            return "correct"
        return "wrong question named"
    if expected == "needs_review":
        return "unclear decided"
    if expected in BLOCKING and given == "different":
        return "copy let in"
    if expected == "different" and given in BLOCKING:
        return "new question blocked"
    if given == "needs_review":
        return "sent to a person"
    return "wrong kind of block"  # one blocking label given for the other


def search_once(corpus: list[dict], candidates: list[dict]) -> dict[str, dict]:
    """Run the exact check and the meaning search for every candidate."""
    index = QuestionIndex(LocalEmbedder(EMBEDDING_MODEL))
    index.add([(q["id"], q["text"]) for q in corpus])
    found = {}
    for candidate in candidates:
        copies = index.exact_matches(candidate["text"])
        shown = [] if copies else index.nearest(candidate["text"], SHOWN_TO_JUDGE)
        found[candidate["id"]] = {
            "exact_copies": copies,
            "shown": [(n.id, n.text) for n in shown],
            "scores": [round(n.score, 4) for n in shown],
        }
    return found


def run_judge(provider: str, model: str, to_judge: list[dict], found: dict[str, dict]) -> tuple[dict[str, Verdict], ChatModel]:
    chat = ChatModel(provider, model)
    judge = Judge(chat)
    verdicts = {}
    for number, candidate in enumerate(to_judge, start=1):
        verdicts[candidate["id"]] = judge.judge(candidate["text"], found[candidate["id"]]["shown"])
        if number % 10 == 0:
            print(f"{chat.name}: {number}/{len(to_judge)}", flush=True)
    return verdicts, chat


def main() -> None:
    corpus = load_corpus()
    candidates = load_answer_key()
    group = duplicate_groups(corpus)

    found = search_once(corpus, candidates)
    to_judge = [c for c in candidates if not found[c["id"]]["exact_copies"]]

    # The judge can only name what it was shown: check how often the partner was shown at all.
    partnered = [c for c in to_judge if c["label"] != "different"]
    partner_shown = [
        c for c in partnered if {group[q] for q in c["of"]} <= {group[qid] for qid, _ in found[c["id"]]["shown"]}
    ]
    exact_right = sum(
        bool(found[c["id"]]["exact_copies"]) == (c["label"] == "exact_duplicate") for c in candidates
    )
    print(f"Exact check: {exact_right}/{len(candidates)} candidates handled correctly by text alone.")
    print(f"Search: every expected partner shown to the judge for {len(partner_shown)}/{len(partnered)} questions.")

    with ThreadPoolExecutor(max_workers=len(CANDIDATE_JUDGES)) as pool:
        futures = {
            f"{provider}/{model}": pool.submit(run_judge, provider, model, to_judge, found)
            for provider, model in CANDIDATE_JUDGES
        }

    results = {}
    for name, future in futures.items():
        verdicts, chat = future.result()
        rows = []
        for candidate in to_judge:
            verdict = verdicts[candidate["id"]]
            rows.append(
                {
                    "id": candidate["id"],
                    "expected": candidate["label"],
                    "given": verdict.label,
                    "named": list(verdict.matches),
                    "outcome": outcome(
                        candidate["label"],
                        verdict,
                        {group[q] for q in candidate["of"]},
                        {group[q] for q in verdict.matches if q in group},
                    ),
                    "judgement_call": bool(candidate.get("judgement_call")),
                    "confidence": verdict.confidence,
                    "reason": verdict.reason,
                }
            )
        counts = Counter(r["outcome"] for r in rows)
        clear = [r for r in rows if not r["judgement_call"]]
        results[name] = {
            "outcomes": {key: counts.get(key, 0) for key in OUTCOMES},
            "correct_on_clear_cases": f"{sum(r['outcome'] == 'correct' for r in clear)}/{len(clear)}",
            "correct_on_judgement_calls": f"{sum(r['outcome'] == 'correct' for r in rows if r['judgement_call'])}/{len(rows) - len(clear)}",
            "replies_fetched_this_run": chat.replies_fetched,
            "seconds_per_reply_this_run": round(chat.seconds_waiting / chat.replies_fetched, 2) if chat.replies_fetched else None,
            "answers": rows,
        }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as handle:
        json.dump({"embedding_model": EMBEDDING_MODEL, "shown_to_judge": SHOWN_TO_JUDGE, "search": found, "judges": results}, handle, indent=2, ensure_ascii=False)

    short = {"copy let in": "let in", "new question blocked": "blocked", "unclear decided": "unclear", "wrong question named": "wrong Q",
             "sent to a person": "person", "wrong kind of block": "kind", "no answer": "none"}
    header = f"\n{'judge':<30}{'correct':>8}" + "".join(f"{label:>9}" for label in short.values()) + f"{'clear':>8}{'j.calls':>8}{'s/reply':>9}"
    print(header)
    for name, r in results.items():
        o = r["outcomes"]
        print(
            f"{name:<30}{o['correct']:>5}/{len(to_judge)}" + "".join(f"{o[key]:>9}" for key in short)
            + f"{r['correct_on_clear_cases']:>8}{r['correct_on_judgement_calls']:>8}{str(r['seconds_per_reply_this_run']):>9}"
        )


if __name__ == "__main__":
    main()
