"""Speaking Domain state machine (V1.2A)."""

from __future__ import annotations

from app.services.language_grammar_speaking.enums import (
    SpeakingAttemptStatus,
    SpeakingSessionStatus,
    SpeakingTurnStatus,
)
from app.services.language_grammar_speaking.errors import SpeakingStateError

SESSION_TRANSITIONS: dict[SpeakingSessionStatus, frozenset[SpeakingSessionStatus]] = {
    SpeakingSessionStatus.initialized: frozenset(
        {
            SpeakingSessionStatus.active,
            SpeakingSessionStatus.cancelled,
            SpeakingSessionStatus.failed,
        }
    ),
    SpeakingSessionStatus.active: frozenset(
        {
            SpeakingSessionStatus.completing,
            SpeakingSessionStatus.cancelled,
            SpeakingSessionStatus.failed,
        }
    ),
    SpeakingSessionStatus.completing: frozenset(
        {
            SpeakingSessionStatus.completed,
            SpeakingSessionStatus.failed,
        }
    ),
    SpeakingSessionStatus.completed: frozenset(),
    SpeakingSessionStatus.cancelled: frozenset(),
    SpeakingSessionStatus.failed: frozenset(),
}

ATTEMPT_TRANSITIONS: dict[SpeakingAttemptStatus, frozenset[SpeakingAttemptStatus]] = {
    SpeakingAttemptStatus.pending: frozenset(
        {
            SpeakingAttemptStatus.active,
            SpeakingAttemptStatus.cancelled,
            SpeakingAttemptStatus.failed,
        }
    ),
    SpeakingAttemptStatus.active: frozenset(
        {
            SpeakingAttemptStatus.finished,
            SpeakingAttemptStatus.cancelled,
            SpeakingAttemptStatus.failed,
        }
    ),
    SpeakingAttemptStatus.finished: frozenset(),
    SpeakingAttemptStatus.cancelled: frozenset(),
    SpeakingAttemptStatus.failed: frozenset(),
}

TURN_TRANSITIONS: dict[SpeakingTurnStatus, frozenset[SpeakingTurnStatus]] = {
    SpeakingTurnStatus.pending: frozenset(
        {
            SpeakingTurnStatus.open,
            SpeakingTurnStatus.skipped,
            SpeakingTurnStatus.failed,
        }
    ),
    SpeakingTurnStatus.open: frozenset(
        {
            SpeakingTurnStatus.closed,
            SpeakingTurnStatus.failed,
        }
    ),
    SpeakingTurnStatus.closed: frozenset(),
    SpeakingTurnStatus.skipped: frozenset(),
    SpeakingTurnStatus.failed: frozenset(),
}


def assert_session_transition(
    current: SpeakingSessionStatus,
    target: SpeakingSessionStatus,
) -> None:
    allowed = SESSION_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise SpeakingStateError(
            "illegal_session_transition",
            f"{current.value} -> {target.value}",
        )


def assert_attempt_transition(
    current: SpeakingAttemptStatus,
    target: SpeakingAttemptStatus,
) -> None:
    allowed = ATTEMPT_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise SpeakingStateError(
            "illegal_attempt_transition",
            f"{current.value} -> {target.value}",
        )


def assert_turn_transition(
    current: SpeakingTurnStatus,
    target: SpeakingTurnStatus,
) -> None:
    allowed = TURN_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise SpeakingStateError(
            "illegal_turn_transition",
            f"{current.value} -> {target.value}",
        )
