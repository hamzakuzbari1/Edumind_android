"""Deterministic Execution Session state machine (V1.5)."""

from __future__ import annotations

from app.services.language_grammar_skill_executor.errors import SkillExecutorError
from app.services.language_grammar_skill_executor.session import SessionStatus

ALLOWED_TRANSITIONS: dict[SessionStatus, frozenset[SessionStatus]] = {
    SessionStatus.created: frozenset(
        {SessionStatus.initializing, SessionStatus.cancelled, SessionStatus.failed}
    ),
    SessionStatus.initializing: frozenset(
        {SessionStatus.running, SessionStatus.cancelled, SessionStatus.failed}
    ),
    SessionStatus.running: frozenset(
        {
            SessionStatus.waiting_for_student,
            SessionStatus.evaluating,
            SessionStatus.cancelled,
            SessionStatus.failed,
        }
    ),
    SessionStatus.waiting_for_student: frozenset(
        {SessionStatus.evaluating, SessionStatus.cancelled, SessionStatus.failed}
    ),
    SessionStatus.evaluating: frozenset(
        {SessionStatus.completed, SessionStatus.cancelled, SessionStatus.failed}
    ),
    SessionStatus.completed: frozenset(),
    SessionStatus.cancelled: frozenset(),
    SessionStatus.failed: frozenset(),
}


class InvalidSessionTransitionError(SkillExecutorError):
    """Illegal execution session state transition."""


def can_transition(current: SessionStatus, target: SessionStatus) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())


def assert_session_transition(current: SessionStatus, target: SessionStatus) -> None:
    if current is target:
        return
    if not can_transition(current, target):
        raise InvalidSessionTransitionError(
            f"Illegal session transition: {current.value} -> {target.value}"
        )
