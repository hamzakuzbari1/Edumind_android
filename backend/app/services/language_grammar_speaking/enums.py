"""Speaking Domain enums (V1.2A) — no LLM / audio."""

from __future__ import annotations

from enum import StrEnum

SPEAKING_DOMAIN_PACKAGE_VERSION = "1.0.0"
SPEAKING_DOMAIN_SCHEMA_VERSION = 1


class SpeakingSessionStatus(StrEnum):
    initialized = "initialized"
    active = "active"
    completing = "completing"
    completed = "completed"
    cancelled = "cancelled"
    failed = "failed"


class SpeakingAttemptStatus(StrEnum):
    pending = "pending"
    active = "active"
    finished = "finished"
    cancelled = "cancelled"
    failed = "failed"


class SpeakingTurnStatus(StrEnum):
    pending = "pending"
    open = "open"
    closed = "closed"
    skipped = "skipped"
    failed = "failed"


class SpeakingSpeaker(StrEnum):
    system = "system"
    student = "student"
    tutor = "tutor"


class SpeakingCompletionState(StrEnum):
    incomplete = "incomplete"
    partial = "partial"
    complete = "complete"
    cancelled = "cancelled"
    failed = "failed"


class SpeakingLifecyclePhase(StrEnum):
    initialize = "initialize"
    start_session = "start_session"
    start_attempt = "start_attempt"
    next_turn = "next_turn"
    finish_attempt = "finish_attempt"
    complete_session = "complete_session"
    cancel = "cancel"


class SpeakingEventType(StrEnum):
    session_initialized = "SpeakingSessionInitialized"
    session_started = "SpeakingSessionStarted"
    attempt_started = "SpeakingAttemptStarted"
    turn_opened = "SpeakingTurnOpened"
    turn_closed = "SpeakingTurnClosed"
    attempt_finished = "SpeakingAttemptFinished"
    session_completed = "SpeakingSessionCompleted"
    session_cancelled = "SpeakingSessionCancelled"
    session_failed = "SpeakingSessionFailed"
