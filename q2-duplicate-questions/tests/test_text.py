"""The exact-duplicate clean-up: what it must ignore, and what it must never ignore."""

import pytest

from qbank.datasets import duplicate_groups, load_answer_key, load_corpus
from qbank.text import fingerprint, normalise


@pytest.mark.parametrize(
    "variant",
    [
        "what is reflection of light",
        "What is  reflection of light ??",
        "WHAT IS REFLECTION OF LIGHT?",
        "  What is reflection of light?\n",
        "1) What is reflection of light?",
        "Q1. What is reflection of light?",
        "Question 3: What is reflection of light?",
        "(a) What is reflection of light?",
        "- What is reflection of light?",
        "**What is reflection of light?**",
        "What is *reflection of light*?",
        "What is reflection of light​?",
    ],
)
def test_presentation_differences_are_ignored(variant):
    assert normalise(variant) == normalise("What is reflection of light?")


@pytest.mark.parametrize(
    "first, second",
    [
        ("What is 5 + 3?", "What is 5 - 3?"),
        ("What is 5!?", "What is 5?"),
        ("Find f'(x).", "Find f(x)."),
        ("A rod is 2.5 m long.", "A rod is 25 m long."),
        ("Simplify 2*3*4.", "Simplify 234."),
        ("Simplify (a)*(b)*(c).", "Simplify (a)(b)(c)."),
        ("Evaluate 2**3.", "Evaluate 23."),
        ("The ratio is 2:3.", "The ratio is 23."),
        ("What is reflection of light?", "What is refraction of light?"),
        ("The angle of incidence is 30°.", "The angle of incidence is 30."),
    ],
)
def test_meaningful_differences_are_kept(first, second):
    assert normalise(first) != normalise(second)


def test_units_numbers_and_blanks_are_tidied():
    assert normalise("The angle is 30 °. Find 50 % of it.") == "the angle is 30° find 50% of it"
    assert normalise("Water boils at 1,000 hPa and 99.6 °C") == "water boils at 1,000 hpa and 99.6°c"
    assert normalise("Light is called ________.") == normalise("Light is called ___.")


def test_fingerprint_matches_only_when_cleaned_text_matches():
    assert fingerprint("Define the reflection of light.") == fingerprint("define the reflection of light")
    assert fingerprint("Define the reflection of light.") != fingerprint("Define the refraction of light.")


def test_answer_key_exact_duplicates_and_only_those_match_the_corpus():
    """Every 'exact duplicate' in the answer key cleans to its corpus partner, and nothing else does."""
    corpus = load_corpus()
    group = duplicate_groups(corpus)
    cleaned_corpus = {}
    for question in corpus:
        cleaned_corpus.setdefault(normalise(question["text"]), set()).add(group[question["id"]])

    for candidate in load_answer_key():
        matched_groups = cleaned_corpus.get(normalise(candidate["text"]), set())
        if candidate["label"] == "exact_duplicate":
            assert matched_groups == {group[qid] for qid in candidate["of"]}, candidate["id"]
        else:
            assert not matched_groups, candidate["id"]
