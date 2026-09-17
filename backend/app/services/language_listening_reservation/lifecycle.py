"""Lifecycle transition enforcement (Phase 2.2)."""

from __future__ import annotations

from app.services.language_listening_reservation.types import (
    ALLOWED_TRANSITIONS,
    ListeningLessonLifecycleState,
)


class IllegalLifecycleTransitionError(ValueError):
    def __init__(self, current: ListeningLessonLifecycleState, target: ListeningLessonLifecycleState) -> None:
        super().__init__(f"Illegal lifecycle transition: {current.value} -> {target.value}")
        self.current = current
        self.target = target


def assert_transition(
    current: ListeningLessonLifecycleState,
    target: ListeningLessonLifecycleState,
) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise IllegalLifecycleTransitionError(current, target)


def can_transition(
    current: ListeningLessonLifecycleState,
    target: ListeningLessonLifecycleState,
) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())
