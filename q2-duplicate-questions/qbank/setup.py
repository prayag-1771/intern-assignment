"""Builds the working system from the decided parts, so every script and the command line use the same setup.

  search model  Qwen3-Embedding-0.6B, run locally                       (decision D10)
  judges        gpt-oss-120b and qwen3.8-27b, referee gemini-3.8-flash   (decision D11)
  writer        gemini-3.5-flash-lite                                    (decision D12)
  labeler       gemini-3.5-flash-lite, temperature 0                     (decision D12)
"""

from __future__ import annotations

from pathlib import Path

from .bank import QuestionBank
from .concepts import ConceptLabeler, plan_syllabus
from .config import DATA_DIR
from .datasets import load_corpus
from .detector import DuplicateDetector
from .embedders import LocalEmbedder
from .generator import QuestionGenerator
from .judge import Judge, JudgePanel
from .llm import ChatModel

SUBJECT = "Physics: reflection of light"
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"
JUDGES = (("groq", "openai/gpt-oss-120b"), ("groq", "qwen/qwen3.8-27b"))
REFEREE = ("gemini", "gemini-3.8-flash")
WRITER = ("gemini", "gemini-3.5-flash-lite")
LABELER = ("gemini", "gemini-3.5-flash-lite")
WRITER_TEMPERATURE = 0.7  # some variety in what is written; replies are cached, so runs still repeat exactly
BANK_PATH = DATA_DIR / "bank.json"
CORPUS_TAGS = {"subject": "physics", "chapter": "light", "source": "assignment"}


def build_panel() -> JudgePanel:
    first, second = (Judge(ChatModel(p, m)) for p, m in JUDGES)
    return JudgePanel(first, second, Judge(ChatModel(*REFEREE)))


def build_labeler(subject: str = SUBJECT, known: list[str] | None = None) -> ConceptLabeler:
    return ConceptLabeler(ChatModel(*LABELER), subject, known or [])


def build_syllabus(subject: str = SUBJECT) -> list[str]:
    return plan_syllabus(ChatModel(*LABELER), subject)


def corpus_bank(labeler: ConceptLabeler, embedder=None) -> QuestionBank:
    """A bank holding the assignment's ten questions, as given (its duplicates included), with concept labels."""
    bank = QuestionBank(embedder or LocalEmbedder(EMBEDDING_MODEL))
    for question in load_corpus():
        label = labeler.label(question["text"])
        bank.add(question["text"], CORPUS_TAGS, label.concept if label else None, label.task if label else None, question["id"])
    return bank


def build_system(bank_path: Path | None = BANK_PATH, subject: str = SUBJECT):
    """The bank (loaded, or started from the assignment's questions), detector and generator."""
    syllabus = build_syllabus(subject)
    labeler = build_labeler(subject, syllabus)
    if bank_path is not None and bank_path.exists():
        bank = QuestionBank.load(bank_path, LocalEmbedder(EMBEDDING_MODEL))
        labeler.known += [c for c in bank.coverage() if c not in labeler.known]
    else:
        bank = corpus_bank(labeler)
    detector = DuplicateDetector(bank.index, build_panel(), labeler)
    writer = ChatModel(*WRITER, temperature=WRITER_TEMPERATURE)
    generator = QuestionGenerator(writer, bank, detector, subject, syllabus)
    return bank, detector, generator
