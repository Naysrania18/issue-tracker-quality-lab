import json
from pathlib import Path

import pytest

from qtools.duplicates import DuplicateFinder, evaluate

DATASET = json.loads((Path(__file__).resolve().parent.parent / "data" / "labelled_duplicates.json").read_text(encoding="utf-8"))
ISSUES, PAIRS = DATASET["issues"], DATASET["duplicate_pairs"]


def test_new_report_matches_existing_duplicate():
    matches = DuplicateFinder(ISSUES).similar_to("App crashes when I open a PDF attachment")
    assert matches[0].issue_id in {6, 7, 8}


def test_unrelated_report_has_no_matches():
    assert DuplicateFinder(ISSUES).similar_to("Printer driver installation fails on Linux") == []


def test_word_forms_still_match():
    # "synchronising" vs "sync": character n-grams make this work.
    matches = DuplicateFinder(ISSUES).similar_to("Synchronising a huge mailbox hangs forever")
    assert matches and matches[0].issue_id in {1, 2, 3}


def test_all_pairs_sorted_by_score():
    scores = [s for _, _, s in DuplicateFinder(ISSUES).all_pairs()]
    assert scores == sorted(scores, reverse=True)


def test_top_n_limits_results():
    assert len(DuplicateFinder(ISSUES, threshold=0.0).similar_to("crash", top_n=3)) == 3


def test_empty_issue_list_rejected():
    with pytest.raises(ValueError):
        DuplicateFinder([])


def test_quality_on_labelled_data_at_default_threshold():
    """Guards the algorithm: if a change makes the finder clearly worse, this fails.

    The data set is tiny and the threshold was tuned on it, so we require a safe floor rather than 1.0.
    """
    result = evaluate(ISSUES, PAIRS, threshold=0.26)
    assert result.precision >= 0.8
    assert result.recall >= 0.8


def test_evaluate_counts_errors_correctly():
    issues = [
        {"id": 1, "title": "login button broken", "description": ""},
        {"id": 2, "title": "login button is broken", "description": ""},
        {"id": 3, "title": "totally different printing issue", "description": ""},
    ]
    perfect = evaluate(issues, [[1, 2]], threshold=0.5)
    assert (perfect.true_positives, perfect.false_positives, perfect.false_negatives) == (1, 0, 0)
    missed = evaluate(issues, [[1, 2], [1, 3]], threshold=0.5)
    assert missed.false_negatives == 1 and missed.recall == 0.5
