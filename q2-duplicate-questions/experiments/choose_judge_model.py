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
from qbank.detector import SHOWN_BY_MEANING
from qbank.embedders import LocalEmbedder
from qbank.judge import Judge, JudgePanel, Verdict
from qbank.llm import ChatModel
from qbank.search import QuestionIndex

RESULTS_PATH = Path(__file__).resolve().parent / "results" / "judge_model_choice.json"
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"  # decision D10

# (service, model, may send new requests). gemini-3.8-flash allows only 20 requests a day, so on
# its own it answers from saved replies; its allowance is kept for its referee job in the panel.
CANDIDATE_JUDGES = [
    ("groq", "openai/gpt-oss-120b", True),
    ("groq", "openai/gpt-oss-20b", True),
    ("groq", "qwen/qwen3.8-27b", True),
    ("gemini", "gemini-3.8-flash", False),
    ("gemini", "gemini-3.5-flash-lite", True),
]
# The setup chosen in decision D11: two judges, and a referee only when they disagree.
PANEL = (("groq", "openai/gpt-oss-120b"), ("groq", "qwen/qwen3.8-27b"), ("gemini", "gemini-3.8-flash"))
PANEL_NAME = "panel: gpt-oss-120b + qwen3.8-27b, referee gemini-3.8-flash"

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
        shown = [] if copies else index.nearest(candidate["text"], SHOWN_BY_MEANING)
        found[candidate["id"]] = {
            "exact_copies": copies,
            "shown": [(n.id, n.text) for n in shown],
            "scores": [round(n.score, 4) for n in shown],
        }
    return found


def run_judge(judge, name: str, to_judge: list[dict], found: dict[str, dict]) -> dict[str, Verdict]:
    verdicts = {}
    for number, candidate in enumerate(to_judge, start=1):
        verdicts[candidate["id"]] = judge.judge(candidate["text"], found[candidate["id"]]["shown"])
        if number % 10 == 0:
            print(f"{name}: {number}/{len(to_judge)}", flush=True)
    return verdicts


def score(verdicts: dict[str, Verdict], to_judge: list[dict], group: dict[str, str], chats: list[ChatModel]) -> dict:
    """Sort every answer into an outcome and summarise it, overall and for each kind of question."""
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
                "added_after_first_tests": "added" in candidate,
                "confidence": verdict.confidence,
                "reason": verdict.reason,
            }
        )
    counts = Counter(r["outcome"] for r in rows)
    if counts["no answer"] == len(rows):
        # Not a single usable reply: the service could not be used, so there is nothing to score.
        return {"unavailable": rows[0]["reason"], "answers": rows}

    def right(subset):
        return f"{sum(r['outcome'] == 'correct' for r in subset)}/{len(subset)}"

    fetched = sum(c.replies_fetched for c in chats)
    return {
        "outcomes": {key: counts.get(key, 0) for key in OUTCOMES},
        # Per kind of question, because the answer key's mix of kinds is not the real-world mix:
        # one overall score would depend on how many of each kind we happened to write.
        "correct_by_expected_label": {
            label: right([r for r in rows if r["expected"] == label]) for label in sorted({r["expected"] for r in rows})
        },
        "correct_on_clear_cases": right([r for r in rows if not r["judgement_call"]]),
        "correct_on_judgement_calls": right([r for r in rows if r["judgement_call"]]),
        "correct_on_questions_added_after_first_tests": right([r for r in rows if r["added_after_first_tests"]]),
        "replies_fetched_this_run": fetched,
        # Speed of the models themselves; waits caused by rate limits and quotas are left out.
        "seconds_per_reply_this_run": round(sum(c.seconds_answering for c in chats) / fetched, 2) if fetched else None,
        "answers": rows,
    }


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

    # Each model runs in its own thread with its own cache file, so they do not overwrite each other.
    chats = {f"{p}/{m}": ChatModel(p, m, allow_requests=live) for p, m, live in CANDIDATE_JUDGES}
    with ThreadPoolExecutor(max_workers=len(chats)) as pool:
        futures = {name: pool.submit(run_judge, Judge(chat), name, to_judge, found) for name, chat in chats.items()}
    results = {name: score(future.result(), to_judge, group, [chats[name]]) for name, future in futures.items()}

    # The chosen setup runs afterwards, so its two judges find their answers already saved;
    # only the referee may need new requests, and only where the judges disagree.
    panel_chats = [ChatModel(p, m) for p, m in PANEL]
    panel = JudgePanel(*(Judge(chat) for chat in panel_chats))
    results[PANEL_NAME] = score(run_judge(panel, PANEL_NAME, to_judge, found), to_judge, group, panel_chats)

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as handle:
        json.dump({"embedding_model": EMBEDDING_MODEL, "shown_to_judge": SHOWN_BY_MEANING, "search": found, "judges": results}, handle, indent=2, ensure_ascii=False)

    short = {"copy let in": "let in", "new question blocked": "blocked", "unclear decided": "unclear", "wrong question named": "wrong Q",
             "sent to a person": "person", "wrong kind of block": "kind", "no answer": "none"}
    header = f"\n{'judge':<62}{'correct':>8}" + "".join(f"{label:>9}" for label in short.values()) + f"{'clear':>8}{'j.calls':>8}{'added':>7}"
    print(header)
    for name, r in results.items():
        if "unavailable" in r:
            print(f"{name:<62}  not scored: {r['unavailable'][:100]}")
            continue
        o = r["outcomes"]
        print(
            f"{name:<62}{o['correct']:>5}/{len(to_judge)}" + "".join(f"{o[key]:>9}" for key in short)
            + f"{r['correct_on_clear_cases']:>8}{r['correct_on_judgement_calls']:>8}"
            + f"{r['correct_on_questions_added_after_first_tests']:>7}"
        )
    print("\nCorrect by kind of question:")
    for name, r in results.items():
        if "outcomes" in r:
            print(f"  {name:<62}" + "  ".join(f"{k}: {v}" for k, v in r["correct_by_expected_label"].items()))


if __name__ == "__main__":
    main()
