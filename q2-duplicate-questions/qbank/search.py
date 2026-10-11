"""The question bank's search stage: exact lookups and nearest-by-meaning lookups.

Exact lookups use the cleaned-text fingerprint, so finding a copy is one dictionary
lookup however large the bank is. Meaning lookups compare the new question's vector
with every stored vector in one matrix product. That is exact (nothing is skipped)
and fast for tens of thousands of questions; beyond that, an approximate index such
as FAISS can replace the matrix product without changing anything else.
"""

from __future__ import annotations

from typing import NamedTuple, Sequence

import numpy as np

from .embedders import Embedder
from .text import fingerprint, normalise


class Neighbour(NamedTuple):
    id: str
    text: str
    score: float


class QuestionIndex:
    """The stored questions, their fingerprints and their vectors."""

    def __init__(self, embedder: Embedder):
        self._embedder = embedder
        self._ids: list[str] = []
        self._texts: list[str] = []
        self._by_fingerprint: dict[str, list[str]] = {}
        self._vectors: np.ndarray | None = None

    def __len__(self) -> int:
        return len(self._ids)

    def add(self, questions: Sequence[tuple[str, str]]) -> None:
        """Store questions given as (id, text) pairs."""
        if not questions:
            return
        known = set(self._ids)
        for qid, text in questions:
            if qid in known:
                raise ValueError(f"Question id {qid!r} is already stored.")
            known.add(qid)
            self._ids.append(qid)
            self._texts.append(text)
            self._by_fingerprint.setdefault(fingerprint(text), []).append(qid)
        vectors = self._embedder.embed([text for _, text in questions])
        self._vectors = vectors if self._vectors is None else np.vstack([self._vectors, vectors])

    def exact_matches(self, text: str) -> list[str]:
        """Ids of stored questions whose cleaned text equals the cleaned new text."""
        return list(self._by_fingerprint.get(fingerprint(text), []))

    def nearest(self, text: str, k: int) -> list[Neighbour]:
        """The k stored questions closest in meaning, most similar first.

        Stored questions that are exact copies of one already listed are skipped,
        so the k places are not used up by the same wording twice.
        """
        if self._vectors is None or k <= 0:
            return []
        scores = self._vectors @ self._embedder.embed([text])[0]
        found: list[Neighbour] = []
        listed_wordings: set[str] = set()
        for row in np.argsort(-scores, kind="stable"):
            wording = normalise(self._texts[row])
            if wording in listed_wordings:
                continue
            listed_wordings.add(wording)
            found.append(Neighbour(self._ids[row], self._texts[row], float(scores[row])))
            if len(found) == k:
                break
        return found
