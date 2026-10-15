"""The LLM judge: decides how a new question relates to the few existing questions nearest to it.

The judge is given the written rule the project agreed on (the perfect-answer test)
and sees the nearest existing questions together, so it can notice a new question
that joins two of them. It never decides alone on anything it cannot read clearly:
an unusable or missing reply becomes "needs_review", which holds the question for
a person instead of letting a possible duplicate through.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .llm import LLMUnavailable

# Exact duplicates are found by text matching before the judge is asked, so it has four labels.
JUDGE_LABELS = ("semantic_duplicate", "variant", "needs_review", "different")

SYSTEM_PROMPT = """You check whether a NEW exam question repeats questions that are ALREADY in a question bank.

Use the perfect-answer test: two questions are the same if a perfect answer to one would earn full marks on the other. Apply it by comparing two things for each question:
- concept: what the question is about
- task: what the student must do (define, state, explain why, calculate, compare, give examples, draw, and so on)

Choose exactly one label for the NEW question:
- "semantic_duplicate": the same concept and the same task as an existing question, in different words or a different format such as multiple choice or fill in the blank. Also use this when the new question is only two or more existing questions joined together, and list all of them.
- "variant": the same concept, task and method as an existing question; only the numbers or names differ.
- "needs_review": the new question is broader, narrower or vaguer than an existing one, or asks for only part of it, so whether it is a repeat depends on context.
- "different": no existing question has the same concept and task. A question about another concept is different even when only one word changes. The same concept with another task is different.

Judge by what the questions ask, not by how many words they share.

Examples, with existing questions [E1] "State Ohm's law." and [E2] "A 10 ohm resistor carries a current of 2 A. Find the voltage across it.":
- "Write the statement of Ohm's law." is semantic_duplicate of E1.
- "A 5 ohm resistor carries a current of 3 A. What is the voltage across it?" is variant of E2.
- "State Ohm's law, then find the voltage across a 10 ohm resistor carrying 2 A." is semantic_duplicate of E1 and E2.
- "Which quantity does Ohm's law say is proportional to voltage?" is needs_review against E1.
- "State Kirchhoff's current law." is different.
- "Describe an experiment to verify Ohm's law." is different.

Reply with JSON only, in this form:
{"concept": "<concept of the new question>", "task": "<task of the new question>", "label": "<one label>", "matches": ["<id of every existing question it repeats or relates to; empty when different>"], "reason": "<at most 25 words>", "confidence": <whole number from 1 to 5>}"""


class JsonModel(Protocol):
    """Anything that answers a system and user message with a JSON object, such as llm.ChatModel."""

    def ask_json(self, system: str, user: str) -> dict: ...


@dataclass(frozen=True)
class Verdict:
    label: str
    matches: tuple[str, ...]
    reason: str
    confidence: int
    # False when the model gave no usable answer and the question was held for review instead.
    judged: bool = True


def _held(reason: str) -> Verdict:
    return Verdict("needs_review", (), reason, 0, judged=False)


def build_user_message(new_question: str, existing: Sequence[tuple[str, str]]) -> str:
    """Lay out the existing questions (id, text) and the new question for the judge."""
    lines = ["Existing questions:"]
    lines += [f"[{qid}] {text}" for qid, text in existing]
    lines += ["", "New question:", new_question]
    return "\n".join(lines)


class Judge:
    def __init__(self, model: JsonModel):
        self._model = model

    def judge(self, new_question: str, existing: Sequence[tuple[str, str]]) -> Verdict:
        """Label the new question against the existing questions shown to the judge."""
        try:
            reply = self._model.ask_json(SYSTEM_PROMPT, build_user_message(new_question, existing))
        except LLMUnavailable as error:
            return _held(f"Judge unavailable: {error}")
        except ValueError:
            return _held("Judge reply was not valid JSON.")
        return _read_verdict(reply, {qid for qid, _ in existing})


class JudgePanel:
    """Two judges must agree; a referee is asked only when they do not (decision D11).

    The referee's answer counts when it matches one of the two judges. Otherwise, or
    when the referee cannot answer, the question is held for a person: disagreement
    between two different models is the signal that the question is unclear.
    """

    def __init__(self, first: Judge, second: Judge, referee: Judge | None = None):
        self._first, self._second, self._referee = first, second, referee

    def judge(self, new_question: str, existing: Sequence[tuple[str, str]]) -> Verdict:
        a = self._first.judge(new_question, existing)
        b = self._second.judge(new_question, existing)
        if a.judged and b.judged and a.label == b.label:
            return _agreed(a.label, [a, b])

        votes = [v for v in (a, b) if v.judged]
        r = self._referee.judge(new_question, existing) if self._referee else None
        if r is not None and r.judged:
            backing = [v for v in votes if v.label == r.label]
            if backing:
                return _agreed(r.label, [r, *backing])
        said = "; ".join(f"{name} said {v.label if v.judged else 'nothing usable'}" for name, v in
                         [("first judge", a), ("second judge", b)] + ([("referee", r)] if r is not None else []))
        named = tuple(dict.fromkeys(m for v in (a, b, r) if v is not None for m in v.matches))
        if not votes:
            return _held(f"No judge gave a usable answer ({said}).")
        return Verdict("needs_review", named, f"The judges disagree: {said}.", 0)


def _agreed(label: str, verdicts: list[Verdict]) -> Verdict:
    matches = () if label == "different" else tuple(dict.fromkeys(m for v in verdicts for m in v.matches))
    return Verdict(label, matches, verdicts[0].reason, min(v.confidence for v in verdicts))


def _read_verdict(reply: dict, known_ids: set[str]) -> Verdict:
    label = reply.get("label")
    if label not in JUDGE_LABELS:
        return _held(f"Judge gave an unknown label: {label!r}.")

    listed = reply.get("matches") or []
    if not isinstance(listed, list):
        listed = [listed]
    # Models sometimes write "[Q7]" for "Q7"; ids that were never shown are dropped.
    matches = tuple(m for m in (str(item).strip("[] ") for item in listed) if m in known_ids)
    if label == "different":
        matches = ()
    elif not matches:
        return _held(f"Judge said {label} but named no existing question.")

    try:
        confidence = min(max(int(reply.get("confidence", 0)), 0), 5)
    except (TypeError, ValueError):
        confidence = 0
    return Verdict(label, matches, str(reply.get("reason", "")).strip(), confidence)
