"""Generation-time duplicate avoidance: the memory-guided loop (decision D5).

Each round the writer's prompt is rebuilt from the bank:
  - a coverage summary: the concepts the bank covers and how many questions each has;
  - the concepts with fewest questions, to aim at;
  - the stored questions nearest to those concepts and to the subject, marked "already asked";
  - last round's rejected questions, with the reason.
Every part has a fixed maximum size, so the prompt stays the same size however large
the bank grows; the bank is searched, never pasted in whole.

Each new question is then checked by the independent detector. Only "different"
questions join the bank; "needs review" ones are held for a person (D9); the rest are
rejected and fed back. The detector labels the question's concept itself and ignores
the concept the writer claims, so prevention and detection stay independent.
"""

from __future__ import annotations

from dataclasses import dataclass

from .bank import QuestionBank
from .detector import Detection, DuplicateDetector
from .judge import JsonModel
from .llm import LLMUnavailable

COVERAGE_SHOWN = 20
GAPS_SHOWN = 5
ALREADY_ASKED_SHOWN = 12
FEEDBACK_SHOWN = 10

WRITER_PROMPT = """You write new exam questions for a question bank. Every question you write must test something that no question in the bank already tests.

A question is NOT new if it only rewords an existing question, changes its numbers or names, changes its format (multiple choice, fill in the blank, true or false), asks for only part of it, or joins existing questions together.
A question IS new if it tests a concept the bank does not cover, or a covered concept with a different task (for example explain why, calculate, compare, give an example, draw, describe an experiment).

Each question must be clear, correct for the subject, answerable by a school student, and different from the other questions you write.
Reply with JSON only: {"questions": [{"question": "...", "concept": "<the syllabus point it tests>", "task": "<what the student must do>"}]}"""

NAIVE_PROMPT = """You write exam questions for a school subject. Each question must be clear, correct and answerable by a school student.
Reply with JSON only: {"questions": [{"question": "...", "concept": "<the syllabus point it tests>", "task": "<what the student must do>"}]}"""


@dataclass
class Attempt:
    round: int
    text: str
    claimed_concept: str  # what the writer said it tests; recorded, never used for checking
    detection: Detection | None
    outcome: str  # "accepted", "held", "rejected", or "not checked" once enough were accepted
    stored_id: str | None = None


class QuestionGenerator:
    def __init__(self, writer: JsonModel, bank: QuestionBank, detector: DuplicateDetector, subject: str, syllabus: list[str]):
        self._writer = writer
        self._bank = bank
        self._detector = detector
        self.subject = subject
        self.syllabus = syllabus

    def build_prompt(self, count: int, rejected: list[Attempt]) -> str:
        """The writer's message for one round: bounded summaries of the bank, never the whole bank."""
        coverage = self._bank.coverage()
        lines = [f"Subject: {self.subject}", f"Write {count} new questions.", "", "Coverage of the bank (concept: number of questions):"]
        top = coverage.most_common(COVERAGE_SHOWN)
        lines += [f"- {concept}: {n}" for concept, n in top] or ["- (empty)"]
        if len(coverage) > len(top):
            lines.append(f"- and {len(coverage) - len(top)} more concepts")

        gaps = sorted(self.syllabus, key=lambda c: (coverage.get(c, 0), self.syllabus.index(c)))[:GAPS_SHOWN]
        lines += ["", "Concepts with few or no questions; aim at these first:"]
        lines += [f"- {concept} ({coverage.get(concept, 0)} so far)" for concept in gaps]

        asked: dict[str, str] = {}
        for query in gaps + [self.subject]:
            for n in self._bank.index.nearest(query, 3 if query != self.subject else ALREADY_ASKED_SHOWN):
                if len(asked) < ALREADY_ASKED_SHOWN:
                    asked.setdefault(n.id, n.text)
        lines += ["", "Questions already in the bank (do not repeat, reword, renumber or reformat them):"]
        lines += [f"- {text}" for text in asked.values()] or ["- (none)"]

        if rejected:
            lines += ["", "Rejected in the last round, and why (do not write these again):"]
            for attempt in rejected[-FEEDBACK_SHOWN:]:
                d = attempt.detection
                repeats = ", ".join(self._bank.questions[m].text for m in d.matches if m in self._bank.questions)
                lines.append(f'- "{attempt.text}": {d.label.replace("_", " ")}' + (f' of "{repeats}"' if repeats else ""))
        return "\n".join(lines)

    def generate(self, wanted: int, max_rounds: int = 4, spare: int = 2, tags: dict | None = None) -> list[Attempt]:
        """Generate until `wanted` new questions are accepted or the rounds run out."""
        attempts: list[Attempt] = []
        accepted = 0
        rejected: list[Attempt] = []
        for round_number in range(1, max_rounds + 1):
            if accepted >= wanted:
                break
            user = self.build_prompt(wanted - accepted + spare, rejected)
            try:
                items = self._writer.ask_json(WRITER_PROMPT, user).get("questions", [])
            except (LLMUnavailable, ValueError):
                break
            rejected = []
            for item in items:
                attempt = self._check(round_number, item, accepted >= wanted, tags)
                if attempt is None:
                    continue
                attempts.append(attempt)
                accepted += attempt.outcome == "accepted"
                if attempt.outcome == "rejected":
                    rejected.append(attempt)
        return attempts

    def _check(self, round_number: int, item: dict, enough: bool, tags: dict | None) -> Attempt | None:
        text = str(item.get("question", "")).strip() if isinstance(item, dict) else ""
        if not text:
            return None
        claimed = str(item.get("concept", ""))
        if enough:
            return Attempt(round_number, text, claimed, None, "not checked")
        detection = self._detector.check(text)
        concept = detection.concept.concept if detection.concept else None
        task = detection.concept.task if detection.concept else None
        tags = {"source": "generated", **(tags or {})}
        if detection.label == "different":
            stored = self._bank.add(text, tags, concept, task)
            return Attempt(round_number, text, claimed, detection, "accepted", stored.id)
        if detection.label == "needs_review":
            stored = self._bank.hold(text, tags, concept, task, note=detection.reason)
            return Attempt(round_number, text, claimed, detection, "held", stored.id)
        return Attempt(round_number, text, claimed, detection, "rejected")


def generate_naively(writer: JsonModel, bank: QuestionBank, detector: DuplicateDetector, subject: str, count: int) -> list[Attempt]:
    """The baseline for comparison: the writer sees only the subject, never the bank.

    Its questions go through the same detector and the same bank rules, so the share
    that the detector rejects shows how much the memory-guided prompt prevents.
    """
    reply = writer.ask_json(NAIVE_PROMPT, f"Subject: {subject}\nWrite {count} questions.")
    loop = QuestionGenerator(writer, bank, detector, subject, [])
    attempts = []
    for item in reply.get("questions", [])[:count]:
        attempt = loop._check(1, item, False, {"source": "generated-naively"})
        if attempt is not None:
            attempts.append(attempt)
    return attempts
