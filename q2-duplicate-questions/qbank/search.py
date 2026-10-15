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
    route: str = "meaning"  # "meaning" (nearest by embedding) or "concept" (same concept label)


class QuestionIndex:
    """The stored questions, their fingerprints, their vectors and their concept labels."""

    def __init__(self, embedder: Embedder):
        self._embedder = embedder
        self._ids: list[str] = []
        self._texts: list[str] = []
        self._by_fingerprint: dict[str, list[str]] = {}
        self._vectors: np.ndarray | None = None
        self._concepts: dict[str, str] = {}

    def __len__(self) -> int:
        return len(self._ids)

    def add(self, questions: Sequence[tuple[str, str]], concepts: Sequence[str | None] | None = None) -> None:
        """Store questions given as (id, text) pairs, optionally with their concept labels."""
        if not questions:
            return
        for (qid, _), concept in zip(questions, concepts or []):
            if concept:
                self._concepts[qid] = concept
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

    def concept_of(self, qid: str) -> str | None:
        return self._concepts.get(qid)

    def nearest(self, text: str, k: int) -> list[Neighbour]:
        """The k stored questions closest in meaning, most similar first."""
        return self.search(text, k)

    def search(self, text: str, k: int, concept: str | None = None, by_concept: int = 0) -> list[Neighbour]:
        """The k stored questions closest in meaning, then up to `by_concept` more that share the concept label.

        The second route (decision D4) catches a duplicate whose wording is too far apart
        for the meaning search to rank it among the nearest k. Stored questions that are
        exact copies of one already listed are skipped, so places are not used up by the
        same wording twice.
        """
        if self._vectors is None or k <= 0:
            return []
        scores = self._vectors @ self._embedder.embed([text])[0]
        found: list[Neighbour] = []
        extra = 0
        listed_wordings: set[str] = set()
        for row in np.argsort(-scores, kind="stable"):
            wording = normalise(self._texts[row])
            if wording in listed_wordings:
                continue
            qid = self._ids[row]
            if len(found) < k:
                route = "meaning"
            elif concept and extra < by_concept and self._concepts.get(qid) == concept:
                route, extra = "concept", extra + 1
            else:
                if len(found) >= k and (not concept or extra >= by_concept):
                    break
                continue
            listed_wordings.add(wording)
            found.append(Neighbour(qid, self._texts[row], float(scores[row]), route))
        return found
