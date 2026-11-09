"""Unit tests for the pure workflow rules (no database, no HTTP)."""
import itertools

import pytest

from app.workflow import ALLOWED_TRANSITIONS, InvalidTransition, State, can_transition, validate_transition

ALL_PAIRS = list(itertools.product(State, State))


@pytest.mark.smoke
@pytest.mark.parametrize(("current", "target"), ALL_PAIRS)
def test_transition_table_matches_rules(current, target):
    expected = target in ALLOWED_TRANSITIONS[current]
    assert can_transition(current, target) is expected


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (State.ANALYZE, State.CLOSED),  # cannot skip straight to Closed
        (State.INTEGRATE, State.CLOSED),
        (State.BUILD, State.CLOSED),  # cannot close without passing Verify
        (State.ANALYZE, State.ANALYZE),  # no self transitions
    ],
)
def test_forbidden_transitions_raise(current, target):
    with pytest.raises(InvalidTransition):
        validate_transition(current, target, role="qa")


def test_only_qa_can_close():
    validate_transition(State.VERIFY, State.CLOSED, role="qa")
    for role in ("engineer", "reporter"):
        with pytest.raises(InvalidTransition):
            validate_transition(State.VERIFY, State.CLOSED, role=role)


def test_failed_verification_goes_back_to_analyze():
    validate_transition(State.VERIFY, State.ANALYZE, role="engineer")


def test_closed_issue_can_only_be_reopened():
    assert ALLOWED_TRANSITIONS[State.CLOSED] == {State.ANALYZE}
