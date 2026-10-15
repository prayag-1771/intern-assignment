"""Command line for the question bank.

    python -m qbank check "Define the reflection of light."
    python -m qbank generate 5
    python -m qbank review
    python -m qbank resolve N7 new        (or: duplicate)
    python -m qbank list source=generated

The bank is kept in data/bank.json; it starts from the assignment's ten questions.
"""

from __future__ import annotations

import sys

from .setup import BANK_PATH, build_system

USAGE = __doc__


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in {"check", "generate", "review", "resolve", "list"}:
        print(USAGE)
        return 2
    command, rest = argv[0], argv[1:]
    bank, detector, generator = build_system()

    if command == "check":
        detection = detector.check(" ".join(rest))
        print(f"{detection.label}  {', '.join(detection.matches) or '-'}  ({detection.method})")
        for qid in detection.matches:
            print(f"  {qid}: {bank.questions[qid].text}")
        print(f"  reason: {detection.reason}")
        return 0

    if command == "generate":
        attempts = generator.generate(int(rest[0]) if rest else 5)
        for a in attempts:
            label = a.detection.label if a.detection else "-"
            print(f"[round {a.round}] {a.outcome:<12} {label:<19} {a.text}")
        bank.save(BANK_PATH)
        return 0

    if command == "review":
        for q in bank.held():
            print(f"{q.id}: {q.text}\n    {q.note}")
        print(f"{len(bank.held())} question(s) waiting for review.")
        return 0

    if command == "resolve":
        qid, decision = rest[0], rest[1]
        bank.resolve(qid, is_new=decision == "new")
        bank.save(BANK_PATH)
        print(f"{qid}: {'added to the bank' if decision == 'new' else 'dropped as a repeat'}.")
        return 0

    filters = dict(pair.split("=", 1) for pair in rest)
    for q in bank.filter(**filters):
        print(f"{q.id}: {q.text}  [{', '.join(f'{k}={v}' for k, v in q.tags.items())}]")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
