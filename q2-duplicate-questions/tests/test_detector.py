"""The search stage and the detector, with a word-count embedder and a stand-in judge so no model or key is needed."""

import zlib

import numpy as np
import pytest

from qbank.detector import DuplicateDetector
from qbank.judge import Judge
from qbank.search import QuestionIndex
from qbank.text import normalise


class WordEmbedder:
    """Counts words into 256 buckets: crude, but enough to make shared words count as similar."""

    name = "word counts"

    def embed(self, texts):
        rows = np.zeros((len(texts), 256), dtype=np.float32)
        for row, text in enumerate(texts):
            for word in normalise(text).split():
                rows[row, zlib.crc32(word.encode()) % 256] += 1
        return rows / np.clip(np.linalg.norm(rows, axis=1, keepdims=True), 1e-12, None)


class StandInModel:
    def __init__(self, reply):
        self._reply = reply
        self.asked = []

    def ask_json(self, system, user):
        self.asked.append(user)
        if isinstance(self._reply, Exception):
            raise self._reply
        return self._reply


BANK = [
    ("Q1", "What is reflection of light?"),
    ("Q2", "Define the reflection of light."),
    ("Q5", "State the laws of reflection of light."),
    ("Q7", "The angle of incidence is 30°. What is the angle of reflection?"),
    ("Q10", "Define the reflection of light."),
]


@pytest.fixture
def index():
    built = QuestionIndex(WordEmbedder())
    built.add(BANK)
    return built


def test_exact_matches_ignore_presentation_and_list_every_copy(index):
    assert index.exact_matches("**define the REFLECTION of light**") == ["Q2", "Q10"]
    assert index.exact_matches("Define the refraction of light.") == []


def test_nearest_lists_most_similar_first_and_skips_repeated_wording(index):
    found = index.nearest("Define reflection of light", k=3)

    assert found[0].id == "Q2"
    assert "Q10" not in [n.id for n in found]  # same wording as Q2, so it would waste a place
    assert len(found) == 3
    assert found[0].score >= found[1].score >= found[2].score


def test_a_stored_id_cannot_be_added_twice(index):
    with pytest.raises(ValueError, match="already stored"):
        index.add([("Q1", "Anything")])


def test_exact_copy_is_caught_without_asking_the_judge(index):
    model = StandInModel({"label": "different", "matches": []})

    detection = DuplicateDetector(index, Judge(model)).check("define the reflection of light")

    assert (detection.label, detection.matches, detection.method) == ("exact_duplicate", ("Q2", "Q10"), "exact_text")
    assert model.asked == []


def test_other_questions_go_to_the_judge_with_the_nearest_ones(index):
    model = StandInModel({"label": "variant", "matches": ["Q7"], "reason": "Only the number changes.", "confidence": 5})

    detection = DuplicateDetector(index, Judge(model), shown_to_judge=2).check(
        "The angle of incidence is 45°. What is the angle of reflection?"
    )

    assert (detection.label, detection.matches, detection.method) == ("variant", ("Q7",), "judge")
    assert detection.blocks
    assert len(detection.shown) == 2 and detection.shown[0].id == "Q7"
    assert "[Q7]" in model.asked[0]


def test_an_unusable_judge_reply_holds_the_question(index):
    model = StandInModel({"label": "maybe", "matches": []})

    detection = DuplicateDetector(index, Judge(model)).check("What is a periscope?")

    assert (detection.label, detection.method) == ("needs_review", "held")
    assert detection.blocks


def test_a_different_question_does_not_block(index):
    model = StandInModel({"label": "different", "matches": [], "reason": "Another concept.", "confidence": 5})

    assert not DuplicateDetector(index, Judge(model)).check("What is refraction of light?").blocks


def test_empty_bank_accepts_anything():
    detection = DuplicateDetector(QuestionIndex(WordEmbedder()), Judge(StandInModel({}))).check("Anything?")

    assert (detection.label, detection.method) == ("different", "empty_bank")
