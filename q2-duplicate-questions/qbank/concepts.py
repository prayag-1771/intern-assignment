"""Concept labels: what each question tests, as a short syllabus point, plus the task it sets.

The labels serve two purposes:
- the detector's second search route (decision D4): stored questions with the same
  concept label are shown to the judge even when their wording is far apart;
- the generator's coverage summary (decision D5): how many questions each concept has,
  and which concepts have few or none.

Labels are read from the question text by an LLM, so duplicate checks stay based on
content. They are not the user's key-value tags, which are never used for duplicates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .judge import JsonModel
from .llm import LLMUnavailable

TASKS = ("define", "state", "explain", "describe", "calculate", "compare", "give_examples", "draw", "experiment", "identify", "other")

SYLLABUS_PROMPT = """You plan exam coverage for a school subject.
List the distinct concepts that exam questions on the given subject can test, at the level of syllabus points: specific enough that two questions on the same point would test the same idea (for example "laws of reflection", not "light").
Give 10 to 15 concepts, each 2 to 6 words, lower case.
Reply with JSON only: {"concepts": ["...", "..."]}"""

LABEL_PROMPT = """You label one exam question with the concept it tests and the task it sets.

concept: the specific idea the question tests, as a syllabus point of 2 to 6 words in lower case. Reuse one of the known concepts, written exactly as listed, whenever it fits. Only when none fits, write a new one.
task: what the student must do, one of: """ + ", ".join(TASKS) + """.

Reply with JSON only: {"concept": "...", "task": "..."}"""


@dataclass(frozen=True)
class ConceptLabel:
    concept: str
    task: str


def _clean(text: object) -> str:
    return " ".join(str(text or "").casefold().split())


def plan_syllabus(model: JsonModel, subject: str) -> list[str]:
    """Ask once for the concepts a subject covers; the generator aims at the ones with fewest questions."""
    reply = model.ask_json(SYLLABUS_PROMPT, f"Subject: {subject}")
    concepts = [_clean(c) for c in reply.get("concepts", []) if _clean(c)]
    return list(dict.fromkeys(concepts))


class ConceptLabeler:
    """Labels questions, reusing labels it has already given so the vocabulary stays small."""

    def __init__(self, model: JsonModel, subject: str, known: Iterable[str] = ()):
        self._model = model
        self._subject = subject
        self.known: list[str] = list(dict.fromkeys(_clean(c) for c in known if _clean(c)))

    def label(self, question: str) -> ConceptLabel | None:
        """The question's concept and task, or None when the model gives no usable answer."""
        listed = "\n".join(f"- {c}" for c in self.known) or "(none yet)"
        user = f"Subject: {self._subject}\nKnown concepts:\n{listed}\n\nQuestion: {question}"
        try:
            reply = self._model.ask_json(LABEL_PROMPT, user)
        except (LLMUnavailable, ValueError):
            return None
        concept, task = _clean(reply.get("concept")), _clean(reply.get("task")).replace(" ", "_")
        if not concept:
            return None
        if concept not in self.known:
            self.known.append(concept)
        return ConceptLabel(concept, task if task in TASKS else "other")
