"""Listening lesson lifecycle states (Phase 2.2)."""

from __future__ import annotations

from enum import StrEnum


class ListeningLessonLifecycleState(StrEnum):
    created = "created"
    queued = "queued"
    reserved = "reserved"
    started = "started"
    completed = "completed"
    reviewed = "reviewed"
    archived = "archived"


# Reservation-row transitions (pool item Created/Queued are content-item states).
ALLOWED_TRANSITIONS: dict[ListeningLessonLifecycleState, frozenset[ListeningLessonLifecycleState]] = {
    ListeningLessonLifecycleState.reserved: frozenset(
        {
            ListeningLessonLifecycleState.started,
            ListeningLessonLifecycleState.archived,
        }
    ),
    ListeningLessonLifecycleState.started: frozenset(
        {
            ListeningLessonLifecycleState.completed,
            ListeningLessonLifecycleState.archived,
        }
    ),
    ListeningLessonLifecycleState.completed: frozenset(
        {
            ListeningLessonLifecycleState.reviewed,
            ListeningLessonLifecycleState.archived,
        }
    ),
    ListeningLessonLifecycleState.reviewed: frozenset({ListeningLessonLifecycleState.archived}),
    ListeningLessonLifecycleState.archived: frozenset(),
    ListeningLessonLifecycleState.created: frozenset({ListeningLessonLifecycleState.queued}),
    ListeningLessonLifecycleState.queued: frozenset({ListeningLessonLifecycleState.reserved}),
}


ACTIVE_RESERVATION_STATES: frozenset[ListeningLessonLifecycleState] = frozenset(
    {
        ListeningLessonLifecycleState.reserved,
        ListeningLessonLifecycleState.started,
    }
)

TERMINAL_RESERVATION_STATES: frozenset[ListeningLessonLifecycleState] = frozenset(
    {
        ListeningLessonLifecycleState.completed,
        ListeningLessonLifecycleState.reviewed,
        ListeningLessonLifecycleState.archived,
    }
)
