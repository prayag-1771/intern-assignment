"""The question bank: stored questions, their key-value tags, and the review list.

Tags are free key-value pairs (subject=physics, grade=8, source=generated, ...); new keys
and values can be added at any time. They are for organising and filtering only: the
duplicate checks never read them, so two questions with different tags can still be
duplicates and two with the same tags can still be different.

A question held for review (decision D9) is kept out of the searchable bank until a
person decides, so it can neither block other questions nor be repeated in prompts.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .embedders import Embedder
from .search import QuestionIndex


@dataclass
class StoredQuestion:
    id: str
    text: str
    tags: dict[str, str] = field(default_factory=dict)  # key-value metadata; never used for duplicate checks
    concept: str | None = None  # read from the text by the concept labeler
    task: str | None = None
    status: str = "accepted"  # "accepted", or "held" while waiting for a person
    note: str = ""  # for a held question: why it was held and what it resembles


class QuestionBank:
    def __init__(self, embedder: Embedder):
        self._embedder = embedder
        self.questions: dict[str, StoredQuestion] = {}
        self.index = QuestionIndex(embedder)  # accepted questions only
        self._next_number = 1

    def _new_id(self) -> str:
        while f"N{self._next_number}" in self.questions:
            self._next_number += 1
        return f"N{self._next_number}"

    def add(self, text: str, tags: dict | None = None, concept: str | None = None, task: str | None = None,
            qid: str | None = None) -> StoredQuestion:
        """Store an accepted question and make it searchable."""
        stored = StoredQuestion(qid or self._new_id(), text, dict(tags or {}), concept, task)
        if stored.id in self.questions:
            raise ValueError(f"Question id {stored.id!r} is already stored.")
        self.questions[stored.id] = stored
        self.index.add([(stored.id, text)], concepts=[concept])
        return stored

    def hold(self, text: str, tags: dict | None = None, concept: str | None = None, task: str | None = None,
             note: str = "") -> StoredQuestion:
        """Keep a question on the review list, outside the searchable bank."""
        stored = StoredQuestion(self._new_id(), text, dict(tags or {}), concept, task, "held", note)
        self.questions[stored.id] = stored
        return stored

    def resolve(self, qid: str, is_new: bool) -> None:
        """A person's decision on a held question: new questions join the bank, repeats are dropped."""
        stored = self.questions[qid]
        if stored.status != "held":
            raise ValueError(f"{qid} is not waiting for review.")
        if is_new:
            stored.status, stored.note = "accepted", ""
            self.index.add([(qid, stored.text)], concepts=[stored.concept])
        else:
            del self.questions[qid]

    def accepted(self) -> list[StoredQuestion]:
        return [q for q in self.questions.values() if q.status == "accepted"]

    def held(self) -> list[StoredQuestion]:
        return [q for q in self.questions.values() if q.status == "held"]

    def filter(self, **tags: str) -> list[StoredQuestion]:
        """Accepted questions whose tags include every given key=value pair."""
        return [q for q in self.accepted() if all(q.tags.get(k) == v for k, v in tags.items())]

    def coverage(self) -> Counter:
        """How many accepted questions test each concept."""
        return Counter(q.concept for q in self.accepted() if q.concept)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"questions": [asdict(q) for q in self.questions.values()]}, handle, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path, embedder: Embedder) -> "QuestionBank":
        """Read a saved bank; vectors are recomputed, so the file stays small and readable."""
        bank = cls(embedder)
        with open(path, encoding="utf-8") as handle:
            saved = [StoredQuestion(**q) for q in json.load(handle)["questions"]]
        bank.questions = {q.id: q for q in saved}
        accepted = bank.accepted()
        bank.index.add([(q.id, q.text) for q in accepted], concepts=[q.concept for q in accepted])
        return bank
