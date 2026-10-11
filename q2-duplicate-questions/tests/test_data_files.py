"""Checks that the data files are well formed, so a typo in the answer key cannot skew results."""

import json
from collections import Counter

from qbank.config import DATA_DIR


def _load(name):
    with open(DATA_DIR / name, encoding="utf-8") as handle:
        return json.load(handle)


def test_corpus_holds_the_ten_assignment_questions():
    questions = _load("corpus.json")["questions"]
    ids = [q["id"] for q in questions]

    assert ids == [f"Q{n}" for n in range(1, 11)]
    for question in questions:
        if question["kind"] in ("semantic_duplicate", "exact_duplicate", "ambiguous"):
            assert question["relates_to"] in ids
        else:
            assert question["relates_to"] is None


def test_answer_key_is_consistent():
    corpus_ids = {q["id"] for q in _load("corpus.json")["questions"]}
    key = _load("labelled_candidates.json")
    candidates = key["candidates"]

    assert len({c["id"] for c in candidates}) == len(candidates)
    assert len({c["text"] for c in candidates}) == len(candidates)
    for candidate in candidates:
        assert candidate["label"] in key["labels"]
        assert set(candidate["of"]) <= corpus_ids
        # A 'different' candidate matches nothing; every other label points at what it matches.
        assert bool(candidate["of"]) == (candidate["label"] != "different")
        assert candidate.get("looks_like") in corpus_ids | {None}


def test_answer_key_covers_every_label():
    counts = Counter(c["label"] for c in _load("labelled_candidates.json")["candidates"])

    assert counts == {
        "exact_duplicate": 10,
        "semantic_duplicate": 17,
        "variant": 3,
        "different": 16,
        "needs_review": 4,
    }
