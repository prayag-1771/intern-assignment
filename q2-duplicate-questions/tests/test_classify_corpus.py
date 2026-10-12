"""How the corpus check compares the detector's answer with the assignment's label."""

from experiments.classify_corpus import EXPECTED_LABEL, agrees
from qbank.datasets import duplicate_groups, load_corpus

CORPUS = {q["id"]: q for q in load_corpus()}
GROUP = duplicate_groups(load_corpus())


def test_every_assignment_kind_has_a_detector_label():
    assert {q["kind"] for q in CORPUS.values()} <= set(EXPECTED_LABEL)


def test_label_and_named_question_must_both_be_right():
    assert agrees(CORPUS["Q1"], "different", (), GROUP)  # the first question is new
    assert agrees(CORPUS["Q3"], "semantic_duplicate", ("Q2",), GROUP)  # Q2 repeats Q1, so naming it is right
    assert not agrees(CORPUS["Q3"], "semantic_duplicate", ("Q5",), GROUP)
    assert agrees(CORPUS["Q8"], "needs_review", ("Q1",), GROUP)
    assert agrees(CORPUS["Q10"], "exact_duplicate", ("Q2",), GROUP)
    assert not agrees(CORPUS["Q7"], "variant", ("Q6",), GROUP)
