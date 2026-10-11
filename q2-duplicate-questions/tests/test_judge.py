"""The judge's handling of model replies, tested with a stand-in model so no key is needed."""

from qbank.judge import SYSTEM_PROMPT, Judge, Verdict, build_user_message
from qbank.llm import LLMUnavailable

EXISTING = [("Q6", "What is the angle of reflection?"), ("Q7", "The angle of incidence is 30°. What is the angle of reflection?")]


class StandInModel:
    """Returns a prepared reply, or raises a prepared error, and records what it was asked."""

    def __init__(self, reply=None, error=None):
        self._reply, self._error = reply, error
        self.asked = []

    def ask_json(self, system, user):
        self.asked.append((system, user))
        if self._error:
            raise self._error
        return self._reply


def test_judge_sends_the_rule_and_all_candidates_together():
    model = StandInModel({"label": "different", "matches": [], "reason": "Another concept.", "confidence": 5})

    Judge(model).judge("What is refraction of light?", EXISTING)

    system, user = model.asked[0]
    assert system == SYSTEM_PROMPT
    assert user == build_user_message("What is refraction of light?", EXISTING)
    assert "[Q6] What is the angle of reflection?" in user and "[Q7]" in user
    assert user.endswith("New question:\nWhat is refraction of light?")


def test_a_clean_reply_becomes_a_verdict():
    model = StandInModel({"label": "variant", "matches": ["Q7"], "reason": "Only the number changes.", "confidence": 5})

    assert Judge(model).judge("The angle of incidence is 45°. What is the angle of reflection?", EXISTING) == Verdict(
        "variant", ("Q7",), "Only the number changes.", 5
    )


def test_a_joined_question_keeps_both_matches():
    model = StandInModel({"label": "semantic_duplicate", "matches": ["[Q6]", "Q7"], "reason": "Both joined.", "confidence": 4})

    assert Judge(model).judge("Define the angle of reflection and find it for 30°.", EXISTING).matches == ("Q6", "Q7")


def test_ids_that_were_never_shown_are_dropped():
    model = StandInModel({"label": "semantic_duplicate", "matches": ["Q7", "Q99"], "reason": "", "confidence": 3})

    assert Judge(model).judge("anything", EXISTING).matches == ("Q7",)


def test_different_never_carries_matches():
    model = StandInModel({"label": "different", "matches": ["Q6"], "reason": "Another task.", "confidence": 4})

    assert Judge(model).judge("anything", EXISTING).matches == ()


def test_unusable_replies_are_held_for_review():
    unknown_label = StandInModel({"label": "duplicate", "matches": ["Q7"]})
    no_match = StandInModel({"label": "variant", "matches": [], "confidence": 5})
    not_json = StandInModel(error=ValueError("bad json"))
    unreachable = StandInModel(error=LLMUnavailable("no key"))

    for model in (unknown_label, no_match, not_json, unreachable):
        verdict = Judge(model).judge("anything", EXISTING)
        assert (verdict.label, verdict.matches, verdict.judged) == ("needs_review", (), False)


def test_a_real_needs_review_verdict_is_marked_as_judged():
    model = StandInModel({"label": "needs_review", "matches": ["Q6"], "reason": "Broader.", "confidence": 3})

    assert Judge(model).judge("What is an angle in optics?", EXISTING).judged is True


def test_odd_confidence_values_do_not_break_the_verdict():
    model = StandInModel({"label": "different", "matches": [], "reason": "x", "confidence": "high"})

    assert Judge(model).judge("anything", EXISTING).confidence == 0
