"""The judge's handling of model replies, tested with a stand-in model so no key is needed."""

from qbank.judge import SYSTEM_PROMPT, Judge, JudgePanel, Verdict, build_user_message
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


def test_not_sure_without_a_named_question_is_still_a_usable_answer():
    model = StandInModel({"label": "needs_review", "matches": [], "reason": "Broader.", "confidence": 3})

    verdict = Judge(model).judge("What is an angle in optics?", EXISTING)

    assert (verdict.label, verdict.matches, verdict.judged) == ("needs_review", (), True)


def test_odd_confidence_values_do_not_break_the_verdict():
    model = StandInModel({"label": "different", "matches": [], "reason": "x", "confidence": "high"})

    assert Judge(model).judge("anything", EXISTING).confidence == 0



def _judge(label, matches=("Q7",), error=None):
    return Judge(StandInModel({"label": label, "matches": list(matches), "reason": label, "confidence": 4}, error=error))


def test_panel_accepts_when_both_judges_agree_without_asking_the_referee():
    referee_model = StandInModel({"label": "different", "matches": []})
    panel = JudgePanel(_judge("variant"), _judge("variant"), Judge(referee_model))

    verdict = panel.judge("anything", EXISTING)

    assert (verdict.label, verdict.matches, verdict.judged) == ("variant", ("Q7",), True)
    assert referee_model.asked == []


def test_panel_follows_the_referee_when_it_backs_one_judge():
    panel = JudgePanel(_judge("semantic_duplicate"), _judge("different", ()), _judge("semantic_duplicate", ("Q6",)))

    verdict = panel.judge("anything", EXISTING)

    assert (verdict.label, set(verdict.matches)) == ("semantic_duplicate", {"Q6", "Q7"})


def test_panel_holds_the_question_when_nobody_agrees():
    panel = JudgePanel(_judge("semantic_duplicate"), _judge("different", ()), _judge("variant"))

    verdict = panel.judge("anything", EXISTING)

    assert (verdict.label, verdict.judged) == ("needs_review", True)
    assert "first judge said semantic_duplicate" in verdict.reason and "referee said variant" in verdict.reason


def test_panel_holds_the_question_when_judges_disagree_and_the_referee_is_unreachable():
    panel = JudgePanel(_judge("variant"), _judge("different", ()), _judge("variant", error=LLMUnavailable("quota")))

    assert panel.judge("anything", EXISTING).label == "needs_review"


def test_one_unreachable_judge_still_needs_the_referee_to_agree():
    unreachable = _judge("variant", error=LLMUnavailable("blocked"))
    backed = JudgePanel(_judge("different", ()), unreachable, _judge("different", ()))
    unbacked = JudgePanel(_judge("different", ()), unreachable, None)

    assert backed.judge("anything", EXISTING).label == "different"
    assert unbacked.judge("anything", EXISTING).label == "needs_review"


def test_a_backup_referee_answers_when_the_first_referee_cannot():
    used_up = _judge("x", error=LLMUnavailable("allowance used up"))
    panel = JudgePanel(_judge("variant"), _judge("different", ()), used_up, _judge("variant"))

    assert panel.judge("anything", EXISTING).label == "variant"


def test_panel_with_no_usable_answer_at_all_is_held_without_a_verdict():
    down = LLMUnavailable("down")
    panel = JudgePanel(_judge("x", error=down), _judge("x", error=down), _judge("x", error=down))

    verdict = panel.judge("anything", EXISTING)

    assert (verdict.label, verdict.judged) == ("needs_review", False)
