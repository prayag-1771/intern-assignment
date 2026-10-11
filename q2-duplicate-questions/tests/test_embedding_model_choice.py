"""Checks on the numbers the embedding-model test reports, using hand-made scores."""

import numpy as np

from experiments.choose_embedding_model import evaluate
from qbank.datasets import load_corpus


def _scores(bank, best):
    """One row of similarity scores: 0.10 everywhere except the given corpus questions."""
    row = np.full(len(bank), 0.10)
    for qid, score in best.items():
        row[[q["id"] for q in bank].index(qid)] = score
    return row


def test_evaluate_counts_nearest_right_and_judge_workload():
    bank = load_corpus()
    candidates = [
        {"id": "A", "label": "exact_duplicate", "of": ["Q5"]},
        {"id": "B", "label": "semantic_duplicate", "of": ["Q1"]},
        {"id": "C", "label": "variant", "of": ["Q7"]},
        {"id": "D", "label": "needs_review", "of": ["Q5"]},
        {"id": "E", "label": "different", "of": []},
        {"id": "F", "label": "different", "of": []},
    ]
    similarity = np.array(
        [
            _scores(bank, {"Q5": 0.99}),
            _scores(bank, {"Q3": 0.90}),  # Q3 repeats Q1, so the nearest question is in the right group
            _scores(bank, {"Q6": 0.80, "Q7": 0.70}),  # nearest is Q6, the wrong question
            _scores(bank, {"Q5": 0.60}),
            _scores(bank, {"Q1": 0.75}),  # scores above the weakest partnered question, so it goes to the judge
            _scores(bank, {"Q9": 0.30}),
        ]
    )

    result = evaluate(similarity, bank, candidates)

    assert (result["nearest_right"], result["partnered"]) == (3, 4)
    assert result["nearest_wrong_ids"] == ["C"]
    # C's partner Q7 is second nearest, so the judge would still be shown it.
    assert (result["partner_in_nearest_three"], result["missed_by_search_ids"]) == (4, [])
    # The plain copy is left out of the cut-off, so the weakest partnered question is D at 0.60.
    assert (result["lowest_partnered_id"], result["lowest_partnered_score"]) == ("D", 0.60)
    assert (result["highest_different_id"], result["highest_different_score"]) == ("E", 0.75)
    assert (result["different_sent_to_judge"], result["different_total"]) == (1, 2)
    # Partnered B, C, D against different E, F: B and C beat both, D beats only F, so 5 wins out of 6.
    assert result["ranking_quality"] == round(5 / 6, 4)


def test_joined_question_is_right_when_nearest_is_either_part():
    bank = load_corpus()
    candidates = [
        {"id": "J", "label": "semantic_duplicate", "of": ["Q1", "Q5"]},
        {"id": "X", "label": "different", "of": []},
    ]
    similarity = np.array([_scores(bank, {"Q5": 0.85}), _scores(bank, {"Q9": 0.20})])

    result = evaluate(similarity, bank, candidates)

    assert result["nearest_right"] == 1
