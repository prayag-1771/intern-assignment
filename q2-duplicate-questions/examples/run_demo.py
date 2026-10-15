"""End-to-end demonstration of Question 2, written to examples/REPORT.md.

1. The assignment's check: Q1 to Q10 in order, each against the questions before it.
2. The scenarios the assignment names: exact duplicates, semantic duplicates, and
   genuinely different questions on the same subject.
3. Generation: the memory-guided loop against a naive baseline that never sees the bank,
   both starting from the assignment's ten questions and checked by the same detector.

Every AI reply is cached in data/llm_cache/, so a rerun repeats the same results without
keys or network. Run from q2-duplicate-questions/:
    python -m examples.run_demo
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from experiments.classify_corpus import agrees
from qbank.bank import QuestionBank
from qbank.datasets import duplicate_groups, load_corpus
from qbank.detector import DuplicateDetector
from qbank.embedders import LocalEmbedder
from qbank.generator import QuestionGenerator, generate_naively
from qbank.llm import ChatModel
from qbank.setup import (
    CORPUS_TAGS, EMBEDDING_MODEL, SUBJECT, WRITER, WRITER_TEMPERATURE,
    build_labeler, build_panel, build_syllabus, corpus_bank,
)

HERE = Path(__file__).resolve().parent
WANTED = 10


def classify_corpus_in_order(embedder, labeler) -> list[dict]:
    corpus = load_corpus()
    group = duplicate_groups(corpus)
    bank = QuestionBank(embedder)
    detector = DuplicateDetector(bank.index, build_panel(), labeler)
    rows = []
    for question in corpus:
        d = detector.check(question["text"])
        label = labeler.label(question["text"])
        bank.add(question["text"], CORPUS_TAGS, label.concept if label else None, label.task if label else None, question["id"])
        rows.append({
            "id": question["id"], "text": question["text"], "assignment": question["expected"],
            "detector": d.label, "matches": list(d.matches), "method": d.method, "reason": d.reason,
            "shown": [(n.id, n.route) for n in d.shown], "agrees": agrees(question, d.label, d.matches, group),
        })
    return rows


def attempt_rows(attempts, bank) -> list[dict]:
    rows = []
    for a in attempts:
        d = a.detection
        rows.append({
            "round": a.round, "question": a.text, "outcome": a.outcome,
            "label": d.label if d else None,
            "repeats": [bank.questions[m].text if m in bank.questions else m for m in (d.matches if d else ())],
            "concept": d.concept.concept if d and d.concept else None,
            "reason": d.reason if d else "",
        })
    return rows


def summarise(rows: list[dict]) -> dict:
    checked = [r for r in rows if r["outcome"] != "not checked"]
    counts = Counter(r["outcome"] for r in checked)
    return {
        "written": len(rows), "checked": len(checked), "accepted": counts["accepted"],
        "rejected": counts["rejected"], "held": counts["held"],
        "rejected_share": round(counts["rejected"] / len(checked), 2) if checked else None,
        "concepts_accepted": len({r["concept"] for r in checked if r["outcome"] == "accepted" and r["concept"]}),
        "rounds": max((r["round"] for r in rows), default=0),
    }


def table(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    out = ["| " + " | ".join(title for title, _ in columns) + " |", "|" + "---|" * len(columns)]
    for row in rows:
        out.append("| " + " | ".join(str(row.get(key, "")).replace("|", "/").replace("\n", " ") for _, key in columns) + " |")
    return "\n".join(out)


def main() -> None:
    embedder = LocalEmbedder(EMBEDDING_MODEL)
    syllabus = build_syllabus()
    print("Syllabus:", syllabus, flush=True)

    corpus_rows = classify_corpus_in_order(embedder, build_labeler(known=syllabus))
    print(f"Assignment check: {sum(r['agrees'] for r in corpus_rows)}/10 agree", flush=True)

    writer = ChatModel(*WRITER, temperature=WRITER_TEMPERATURE)

    naive_labeler = build_labeler(known=syllabus)
    naive_bank = corpus_bank(naive_labeler, embedder)
    naive_detector = DuplicateDetector(naive_bank.index, build_panel(), naive_labeler)
    naive = attempt_rows(generate_naively(writer, naive_bank, naive_detector, SUBJECT, WANTED), naive_bank)
    print("Naive:", summarise(naive), flush=True)

    guided_labeler = build_labeler(known=syllabus)
    guided_bank = corpus_bank(guided_labeler, embedder)
    guided_detector = DuplicateDetector(guided_bank.index, build_panel(), guided_labeler)
    generator = QuestionGenerator(writer, guided_bank, guided_detector, SUBJECT, syllabus)
    first_prompt = generator.build_prompt(WANTED + 2, [])
    guided = attempt_rows(generator.generate(WANTED), guided_bank)
    print("Guided:", summarise(guided), flush=True)

    guided_bank.save(HERE / "demo_bank.json")
    results = {"syllabus": syllabus, "assignment_check": corpus_rows, "naive": naive, "guided": guided,
               "naive_summary": summarise(naive), "guided_summary": summarise(guided), "first_guided_prompt": first_prompt}
    with open(HERE / "demo_results.json", "w", encoding="utf-8") as handle:
        json.dump(results, handle, ensure_ascii=False, indent=2)
    write_report(results)


def write_report(r: dict) -> None:
    agree = sum(row["agrees"] for row in r["assignment_check"])
    lines = [
        "# Question 2 demonstration",
        "",
        "Generated by `python -m examples.run_demo`. Every AI reply is cached in `data/llm_cache/`, so a rerun gives the same results without keys.",
        "",
        "## 1. The assignment's ten questions, checked in order",
        "",
        "Each question is checked against the questions before it, then added to the bank. "
        f"**{agree} of 10 agree with the assignment's expected classification.**",
        "",
        table([{**row, "matches": ", ".join(row["matches"]) or "-", "agrees": "yes" if row["agrees"] else "**no**"} for row in r["assignment_check"]],
              [("ID", "id"), ("Question", "text"), ("Assignment says", "assignment"), ("Detector says", "detector"),
               ("Repeats", "matches"), ("Agrees", "agrees"), ("Judges' reason", "reason")]),
        "",
        "## 2. Generation: memory-guided loop against a naive baseline",
        "",
        f"Both start from the assignment's ten questions, ask for {WANTED} new questions, and use the same independent detector. "
        "The naive writer is told only the subject; the guided writer gets the coverage summary, the gaps, the nearest existing questions and last round's rejections.",
        "",
        table([{"run": "naive", **r["naive_summary"]}, {"run": "memory-guided", **r["guided_summary"]}],
              [("Run", "run"), ("Written", "written"), ("Checked", "checked"), ("Accepted", "accepted"), ("Rejected as repeats", "rejected"),
               ("Held for a person", "held"), ("Share rejected", "rejected_share"), ("Concepts among accepted", "concepts_accepted"), ("Rounds", "rounds")]),
        "",
        "### Naive baseline, question by question",
        "",
        table([{**row, "repeats": "; ".join(row["repeats"]) or "-"} for row in r["naive"]],
              [("Question", "question"), ("Outcome", "outcome"), ("Label", "label"), ("Repeats", "repeats"), ("Concept", "concept")]),
        "",
        "### Memory-guided loop, question by question",
        "",
        table([{**row, "repeats": "; ".join(row["repeats"]) or "-"} for row in r["guided"]],
              [("Round", "round"), ("Question", "question"), ("Outcome", "outcome"), ("Label", "label"), ("Repeats", "repeats"), ("Concept", "concept")]),
        "",
        "### The first prompt the guided writer received",
        "",
        "```text",
        r["first_guided_prompt"],
        "```",
        "",
    ]
    (HERE / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
