"""Issue workflow rules, kept as pure functions so they are trivial to unit test."""
from enum import Enum


class State(str, Enum):
    ANALYZE = "Analyze"
    INTEGRATE = "Integrate"
    BUILD = "Build"
    VERIFY = "Verify"
    CLOSED = "Closed"


# current state -> states it may move to
ALLOWED_TRANSITIONS: dict[State, set[State]] = {
    State.ANALYZE: {State.INTEGRATE},
    State.INTEGRATE: {State.BUILD, State.ANALYZE},
    State.BUILD: {State.VERIFY, State.INTEGRATE},
    State.VERIFY: {State.CLOSED, State.ANALYZE},  # a failed verification goes back to Analyze
    State.CLOSED: {State.ANALYZE},  # reopen
}

# Only QA may close an issue (the "Verify passed" sign-off).
ROLE_RESTRICTED_TARGETS = {State.CLOSED: {"qa"}}


class InvalidTransition(Exception):
    pass


def can_transition(current: State, target: State) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def validate_transition(current: State, target: State, role: str) -> None:
    if not can_transition(current, target):
        raise InvalidTransition(f"Cannot move from {current.value} to {target.value}")
    allowed_roles = ROLE_RESTRICTED_TARGETS.get(target)
    if allowed_roles and role not in allowed_roles:
        raise InvalidTransition(f"Role '{role}' may not move an issue to {target.value}")
