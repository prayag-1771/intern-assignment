"""The independent duplicate detector: exact check, then search, then the LLM judge.

It looks only at the question text and the stored questions. It takes nothing from
the generation step, so it still works as a safety net when generation-time
prevention fails (or when questions arrive from anywhere else).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .judge import Judge, JudgePanel
from .search import Neighbour, QuestionIndex

# How many of the nearest stored questions the judge is shown at once.
SHOWN_TO_JUDGE = 5


@dataclass(frozen=True)
class Detection:
    label: str  # exact_duplicate, semantic_duplicate, variant, needs_review or different
    matches: tuple[str, ...]  # ids of the stored questions it repeats or relates to
    reason: str
    confidence: int  # 1 to 5 from the judge; 5 for an exact match; 0 when held without a verdict
    method: str  # "exact_text", "judge", "held" (the judge gave no usable answer) or "empty_bank"
    shown: tuple[Neighbour, ...] = ()  # what the judge was shown, for review and evaluation

    @property
    def blocks(self) -> bool:
        """True when the question must not enter the bank without a person deciding."""
        return self.label != "different"


class DuplicateDetector:
    def __init__(self, index: QuestionIndex, judge: Judge | JudgePanel, shown_to_judge: int = SHOWN_TO_JUDGE):
        self.index = index
        self._judge = judge
        self._shown_to_judge = shown_to_judge

    def check(self, text: str) -> Detection:
        """Classify one new question against everything stored."""
        copies = self.index.exact_matches(text)
        if copies:
            reason = "Same text once letter case, spacing and punctuation are ignored."
            return Detection("exact_duplicate", tuple(copies), reason, 5, "exact_text")

        shown = tuple(self.index.nearest(text, self._shown_to_judge))
        if not shown:
            return Detection("different", (), "The bank is empty.", 5, "empty_bank")

        verdict = self._judge.judge(text, [(n.id, n.text) for n in shown])
        method = "judge" if verdict.judged else "held"
        return Detection(verdict.label, verdict.matches, verdict.reason, verdict.confidence, method, shown)

    def check_many(self, texts: Sequence[str]) -> list[Detection]:
        return [self.check(text) for text in texts]
