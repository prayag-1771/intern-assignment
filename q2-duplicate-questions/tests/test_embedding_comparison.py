"""Checks on the embedding comparison: the pair labels and the summary numbers it reports."""

from collections import Counter

import numpy as np

from experiments.compare_embeddings import pair_kinds, summarise
from qbank.datasets import load_corpus
from qbank.embedders import _unit_rows


def test_ten_questions_split_into_expected_pair_kinds():
    kinds = pair_kinds(load_corpus())

    # Q1, Q2, Q3, Q4 and Q10 form one group of five, giving 10 duplicate pairs.
    assert Counter(kinds.values()) == {"duplicate": 10, "different": 26, "ambiguous": 5}
    assert kinds[("Q2", "Q10")] == "duplicate"
    assert kinds[("Q6", "Q7")] == "different"
    assert kinds[("Q1", "Q8")] == "ambiguous"
    # Q8 is ambiguous only against the Q1 group; its other pairs are left out.
    assert ("Q5", "Q8") not in kinds


def test_summary_reports_lowest_duplicate_highest_different_and_gap():
    questions = load_corpus()
    ids = [q["id"] for q in questions]
    kinds = pair_kinds(questions)
    row = {qid: i for i, qid in enumerate(ids)}

    similarity = np.full((len(ids), len(ids)), 0.10)
    for (a, b), kind in kinds.items():
        value = {"duplicate": 0.90, "different": 0.30, "ambiguous": 0.60}[kind]
        similarity[row[a], row[b]] = similarity[row[b], row[a]] = value
    similarity[row["Q3"], row["Q4"]] = similarity[row["Q4"], row["Q3"]] = 0.80  # weakest duplicate
    similarity[row["Q6"], row["Q7"]] = similarity[row["Q7"], row["Q6"]] = 0.70  # strongest different
    similarity[row["Q1"], row["Q8"]] = similarity[row["Q8"], row["Q1"]] = 0.65

    summary = summarise(similarity, ids, kinds)

    assert summary["lowest_duplicate"] == 0.80
    assert summary["lowest_duplicate_pair"] == ["Q3", "Q4"]
    assert summary["highest_different"] == 0.70
    assert summary["highest_different_pair"] == ["Q6", "Q7"]
    assert summary["gap"] == 0.10
    assert (summary["ambiguous_low"], summary["ambiguous_high"]) == (0.60, 0.65)
    assert summary["q6_q7"] == 0.70


def test_unit_rows_scales_every_row_to_length_one():
    rows = _unit_rows(np.array([[3.0, 4.0], [0.0, 2.0]]))

    assert np.allclose(np.linalg.norm(rows, axis=1), 1.0)
    assert np.allclose(rows[0], [0.6, 0.8])
