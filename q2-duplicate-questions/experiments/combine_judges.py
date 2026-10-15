"""Score ways of combining several judges, using the answers saved by choose_judge_model.py.

No AI is asked anything here: every scheme is replayed from the saved answers, so all
schemes are compared on exactly the same replies.

Schemes:
  alone          one judge decides
  pair           two judges must agree; if not, the question waits for a person
  pair+referee   two judges; only when they disagree, a third (the referee) is asked,
                 and its answer counts if it matches one of the two; otherwise a person
  majority       three judges vote; two out of three wins; no majority goes to a person
  cascade        a cheap judge decides when it says it is confident (4 or 5 out of 5);
                 otherwise a stronger judge decides

Caution: the schemes are compared on the same 40 questions used to choose them, so the
best score is optimistic and must be checked on questions it has not seen.

Run from q2-duplicate-questions/ after choose_judge_model.py:
    python -m experiments.combine_judges
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from experiments.choose_judge_model import OUTCOMES, RESULTS_PATH as JUDGE_RESULTS
from experiments.choose_judge_model import outcome
from qbank.datasets import duplicate_groups, load_answer_key, load_corpus
from qbank.judge import Verdict

RESULTS_PATH = Path(__file__).resolve().parent / "results" / "judge_combinations.json"


def _verdict(answer: dict) -> Verdict:
    return Verdict(answer["given"], tuple(answer["named"]), "", answer["confidence"], judged=answer["outcome"] != "no answer")


def _together(label: str, answers: list[dict]) -> Verdict:
    named = [q for a in answers if a["given"] == label for q in a["named"]]
    return Verdict(label, tuple(dict.fromkeys(named)), "", 3)


def _to_person(answers: list[dict]) -> Verdict:
    return Verdict("needs_review", tuple(dict.fromkeys(q for a in answers for q in a["named"])), "judges disagree", 3)


def alone(a):
    return lambda q: (_verdict(a[q]), 1)


def pair(a, b):
    def decide(q):
        if a[q]["given"] == b[q]["given"]:
            return _together(a[q]["given"], [a[q], b[q]]), 2
        return _to_person([a[q], b[q]]), 2

    return decide


def pair_with_referee(a, b, referee):
    def decide(q):
        if a[q]["given"] == b[q]["given"]:
            return _together(a[q]["given"], [a[q], b[q]]), 2
        r = referee[q]
        if r["outcome"] != "no answer":
            for side in (a[q], b[q]):
                if r["given"] == side["given"]:
                    return _together(r["given"], [side, r]), 3
        return _to_person([a[q], b[q], r]), 3

    return decide


def majority(*judges):
    def decide(q):
        answers = [j[q] for j in judges]
        label, votes = Counter(x["given"] for x in answers).most_common(1)[0]
        if votes >= 2:
            return _together(label, answers), len(judges)
        return _to_person(answers), len(judges)

    return decide


def cascade(cheap, strong, confident_from=4):
    def decide(q):
        first = cheap[q]
        if first["confidence"] >= confident_from and first["given"] != "needs_review":
            return _verdict(first), 1
        return _verdict(strong[q]), 2

    return decide


def main() -> None:
    with open(JUDGE_RESULTS, encoding="utf-8") as handle:
        judges = json.load(handle)["judges"]
    answers = {name.split("/")[-1]: {x["id"]: x for x in j["answers"]} for name, j in judges.items() if "unavailable" not in j}
    key = {c["id"]: c for c in load_answer_key()}
    group = duplicate_groups(load_corpus())
    big, qwen, small = answers["gpt-oss-120b"], answers["qwen3.8-27b"], answers["gpt-oss-20b"]
    flash, lite = answers["gemini-3.8-flash"], answers["gemini-3.5-flash-lite"]

    schemes = {
        "alone: gpt-oss-120b": alone(big),
        "alone: qwen3.8-27b": alone(qwen),
        "alone: gemini-3.5-flash-lite": alone(lite),
        "pair: gpt-oss-120b + qwen3.8-27b": pair(big, qwen),
        "pair: gpt-oss-120b + gemini-3.5-flash-lite": pair(big, lite),
        "pair+referee: gpt-oss-120b + qwen3.8-27b, referee gemini-3.8-flash": pair_with_referee(big, qwen, flash),
        "pair+referee: gpt-oss-120b + qwen3.8-27b, referee gemini-3.5-flash-lite": pair_with_referee(big, qwen, lite),
        "majority: gpt-oss-120b, qwen3.8-27b, gpt-oss-20b": majority(big, qwen, small),
        "majority: gpt-oss-120b, qwen3.8-27b, gemini-3.5-flash-lite": majority(big, qwen, lite),
        "cascade: gemini-3.5-flash-lite, then gpt-oss-120b": cascade(lite, big),
    }

    results = {}
    for name, decide in schemes.items():
        counts, calls = Counter(), 0
        for qid in big:
            verdict, used = decide(qid)
            calls += used
            candidate = key[qid]
            counts[outcome(candidate["label"], verdict, {group[q] for q in candidate["of"]}, {group[q] for q in verdict.matches if q in group})] += 1
        results[name] = {"outcomes": {o: counts.get(o, 0) for o in OUTCOMES}, "ai_answers_used": calls}

    # How sure the cheap judge said it was on the answers it got wrong: if high, its confidence is no guide.
    lite_confidence_when_wrong = {q: lite[q]["confidence"] for q in lite if lite[q]["outcome"] != "correct"}

    with open(RESULTS_PATH, "w", encoding="utf-8") as handle:
        json.dump({"schemes": results, "flash_lite_confidence_when_wrong": lite_confidence_when_wrong}, handle, indent=2)

    print(f"{'scheme':<72}" + "".join(f"{o[:9]:>10}" for o in OUTCOMES) + f"{'answers':>9}")
    for name, r in results.items():
        print(f"{name:<72}" + "".join(f"{r['outcomes'][o]:>10}" for o in OUTCOMES) + f"{r['ai_answers_used']:>9}")
    print("\nFlash-Lite's confidence (1 to 5) on the answers it got wrong:", lite_confidence_when_wrong)


if __name__ == "__main__":
    main()
