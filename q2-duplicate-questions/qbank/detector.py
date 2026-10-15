"""The independent duplicate detector: exact check, then two search routes, then the LLM judges.

It looks only at the question text and the stored questions. It takes nothing from
the generation step (not even the concept the generator claims for its question), so
it still works as a safety net when generation-time prevention fails, or when
questions arrive from anywhere else.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .concepts import ConceptLabel, ConceptLabeler
from .judge import Judge, JudgePanel
from .search import Neighbour, QuestionIndex

# How many stored questions the judges are shown: the nearest by meaning, plus extra ones
# that share the new question's concept label (the second search route, decision D4).
SHOWN_BY_MEANING = 5
SHOWN_BY_CONCEPT = 3


@dataclass(frozen=True)
class Detection:
    label: str  # exact_duplicate, semantic_duplicate, variant, needs_review or different
    matches: tuple[str, ...]  # ids of the stored questions it repeats or relates to
    reason: str
    confidence: int  # 1 to 5 from the judges; 5 for an exact match; 0 when held without a verdict
    method: str  # "exact_text", "judge", "held" (no judge gave a usable answer) or "empty_bank"
    shown: tuple[Neighbour, ...] = ()  # what the judges were shown, for review and evaluation
    concept: ConceptLabel | None = None  # the new question's concept label, when a labeler is used

    @property
    def blocks(self) -> bool:
        """True when the question must not enter the bank without a person deciding."""
        return self.label != "different"


class DuplicateDetector:
    def __init__(
        self,
        index: QuestionIndex,
        judge: Judge | JudgePanel,
        labeler: ConceptLabeler | None = None,
        shown_by_meaning: int = SHOWN_BY_MEANING,
        shown_by_concept: int = SHOWN_BY_CONCEPT,
    ):
        self.index = index
        self._judge = judge
        self._labeler = labeler
        self._by_meaning = shown_by_meaning
        self._by_concept = shown_by_concept if labeler else 0

    def check(self, text: str) -> Detection:
        """Classify one new question against everything stored."""
        copies = self.index.exact_matches(text)
        if copies:
            reason = "Same text once letter case, spacing and punctuation are ignored."
            return Detection("exact_duplicate", tuple(copies), reason, 5, "exact_text")

        if len(self.index) == 0:
            return Detection("different", (), "The bank is empty.", 5, "empty_bank")

        label = self._labeler.label(text) if self._labeler else None
        shown = tuple(
            self.index.search(text, self._by_meaning, concept=label.concept if label else None, by_concept=self._by_concept)
        )
        verdict = self._judge.judge(text, [(n.id, n.text) for n in shown])
        method = "judge" if verdict.judged else "held"
        return Detection(verdict.label, verdict.matches, verdict.reason, verdict.confidence, method, shown, label)

    def check_many(self, texts: Sequence[str]) -> list[Detection]:
        return [self.check(text) for text in texts]
