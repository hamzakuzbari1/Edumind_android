"""Speaking Domain models & DTOs (V1.2A).

Business model only — no LLM, STT, TTS, or audio streaming.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_grammar_evidence.types import GrammarEvidenceObservation
from app.services.language_grammar_speaking.enums import (
    SPEAKING_DOMAIN_PACKAGE_VERSION,
    SPEAKING_DOMAIN_SCHEMA_VERSION,
    SpeakingAttemptStatus,
    SpeakingCompletionState,
    SpeakingEventType,
    SpeakingSessionStatus,
    SpeakingSpeaker,
    SpeakingTurnStatus,
)


@dataclass(frozen=True, slots=True)
class SpeakingContext:
    """Opaque execution context for a Speaking session — no engine internals."""

    student_id: int
    language_id: int
    activity_id: str
    grammar_targets: tuple[str, ...] = ()
    locale: str = "en"
    lesson_id: str = ""
    runtime_session_id: str = ""
    overall_cefr: str = ""
    extras: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SpeakingTiming:
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0


@dataclass(frozen=True, slots=True)
class SpeakingArtifact:
    """Opaque artifact reference — never an audio blob or UI tree."""

    artifact_id: str
    kind: str = "reference"
    uri: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SpeakingTurn:
    """One ordered turn inside an attempt."""

    turn_id: str
    speaker: SpeakingSpeaker
    sequence: int
    prompt_reference: str = ""
    student_response_reference: str = ""
    duration_ms: int = 0
    status: SpeakingTurnStatus = SpeakingTurnStatus.pending
    notes: str = ""


@dataclass(frozen=True, slots=True)
class SpeakingAttempt:
    """One attempt within a Speaking session."""

    attempt_id: str
    session_id: str
    attempt_number: int
    status: SpeakingAttemptStatus = SpeakingAttemptStatus.pending
    started_at: str = ""
    finished_at: str = ""
    turns: tuple[SpeakingTurn, ...] = ()


@dataclass(frozen=True, slots=True)
class SpeakingResult:
    """Outcome of a finished attempt or completed session."""

    completion_state: SpeakingCompletionState
    warnings: tuple[str, ...] = ()
    artifacts: tuple[SpeakingArtifact, ...] = ()
    timing: SpeakingTiming = field(default_factory=SpeakingTiming)
    raw_outputs: dict[str, str] = field(default_factory=dict)
    notes: str = ""


@dataclass(frozen=True, slots=True)
class SpeakingEvidence:
    """Domain evidence envelope — maps to GrammarEvidenceObservation later."""

    evidence_id: str
    session_id: str
    attempt_id: str
    grammar_targets: tuple[str, ...] = ()
    observation_type_hint: str = "formative"
    attempt_count: int = 1
    correct_count: int = 0
    context: str = "speaking_activity"
    notes: str = ""


@dataclass(frozen=True, slots=True)
class SpeakingSession:
    """Root Speaking activity session."""

    session_id: str
    activity_id: str
    student_id: int
    grammar_targets: tuple[str, ...]
    status: SpeakingSessionStatus = SpeakingSessionStatus.initialized
    created_at: str = ""
    updated_at: str = ""
    language_id: int = 0
    current_attempt_id: str | None = None
    attempts: tuple[SpeakingAttempt, ...] = ()
    result: SpeakingResult | None = None
    evidence: tuple[SpeakingEvidence, ...] = ()
    schema_version: int = SPEAKING_DOMAIN_SCHEMA_VERSION
    package_version: str = SPEAKING_DOMAIN_PACKAGE_VERSION


@dataclass(frozen=True, slots=True)
class SpeakingEvent:
    """Append-only Speaking domain event."""

    sequence: int
    event_type: SpeakingEventType
    session_id: str
    at: str
    attempt_id: str | None = None
    turn_id: str | None = None
    detail: str = ""


@dataclass(frozen=True, slots=True)
class SpeakingSessionView:
    """Public DTO projection of a SpeakingSession."""

    session: SpeakingSession
    status: SpeakingSessionStatus
    attempt_count: int
    turn_count: int
    current_attempt_id: str | None
    events: tuple[SpeakingEvent, ...] = ()
    mapped_observations: tuple[GrammarEvidenceObservation, ...] = ()


# Mutable working state for lifecycle engine (not a persistence model).
@dataclass(slots=True)
class SpeakingState:
    """In-memory lifecycle state machine carrier."""

    session: SpeakingSession
    context: SpeakingContext
    events: list[SpeakingEvent] = field(default_factory=list)
    phases_completed: list[str] = field(default_factory=list)
