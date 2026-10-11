"""How the judge test sorts each answer into an outcome."""

import pytest

from experiments.choose_judge_model import outcome
from qbank.judge import Verdict


def _verdict(label, judged=True):
    return Verdict(label, (), "", 3, judged=judged)


@pytest.mark.parametrize(
    "expected, given, expected_groups, named_groups, result",
    [
        ("semantic_duplicate", "semantic_duplicate", {"Q1"}, {"Q1"}, "correct"),
        ("semantic_duplicate", "semantic_duplicate", {"Q1", "Q5"}, {"Q1"}, "wrong question named"),
        ("different", "different", set(), set(), "correct"),
        ("variant", "different", {"Q7"}, set(), "copy let in"),
        ("different", "semantic_duplicate", set(), {"Q1"}, "new question blocked"),
        ("needs_review", "different", {"Q5"}, set(), "unclear decided"),
        ("needs_review", "semantic_duplicate", {"Q5"}, {"Q5"}, "unclear decided"),
        ("different", "needs_review", set(), {"Q1"}, "sent to a person"),
        ("variant", "semantic_duplicate", {"Q7"}, {"Q7"}, "wrong kind of block"),
    ],
)
def test_each_answer_is_sorted_by_its_effect(expected, given, expected_groups, named_groups, result):
    assert outcome(expected, _verdict(given), expected_groups, named_groups) == result


def test_no_usable_reply_is_its_own_outcome():
    assert outcome("different", _verdict("needs_review", judged=False), set(), set()) == "no answer"
