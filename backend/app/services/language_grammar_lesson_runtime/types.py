"""Types for Grammar Lesson Runtime (G3.2).

Runtime executes frozen GrammarLessonBlueprint.steps only.
Never plans lessons, never scores mastery, never schedules review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.services.language_grammar.enums import GrammarLessonStepKind, GrammarReinforcementSkill

GRAMMAR_RUNTIME_SCHEMA_VERSION = 1
GRAMMAR_RUNTIME_VERSION = "1.1.0"


class GrammarRuntimeState(StrEnum):
    """Deterministic lesson runtime state machine (G3.2)."""

    created = "created"
    ready = "ready"
    running = "running"
    paused = "paused"
    step_completed = "step_completed"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class GrammarRuntimeLifecycle(StrEnum):
    """G0 lifecycle labels — derived projection of GrammarRuntimeState."""

    not_started = "not_started"
    in_progress = "in_progress"
    awaiting_skill_handoff = "awaiting_skill_handoff"
    completed = "completed"
    abandoned = "abandoned"


class GrammarRuntimeEventType(StrEnum):
    lesson_created = "LessonCreated"
    lesson_ready = "LessonReady"
    lesson_started = "LessonStarted"
    lesson_paused = "LessonPaused"
    lesson_resumed = "LessonResumed"
    step_started = "StepStarted"
    step_completed = "StepCompleted"
    lesson_completed = "LessonCompleted"
    lesson_failed = "LessonFailed"
    lesson_cancelled = "LessonCancelled"


def lifecycle_from_state(state: GrammarRuntimeState) -> GrammarRuntimeLifecycle:
    if state in (GrammarRuntimeState.created, GrammarRuntimeState.ready):
        return GrammarRuntimeLifecycle.not_started
    if state is GrammarRuntimeState.completed:
        return GrammarRuntimeLifecycle.completed
    if state in (GrammarRuntimeState.cancelled, GrammarRuntimeState.failed):
        return GrammarRuntimeLifecycle.abandoned
    if state is GrammarRuntimeState.paused:
        return GrammarRuntimeLifecycle.awaiting_skill_handoff
    return GrammarRuntimeLifecycle.in_progress


@dataclass(frozen=True, slots=True)
class GrammarRuntimeCursor:
    """Cursor over Blueprint.steps — Runtime advances this only."""

    blueprint_fingerprint: str
    step_index: int
    current_step_id: str | None
    current_step_kind: GrammarLessonStepKind | None
    current_reinforcement_skill: GrammarReinforcementSkill | None = None


@dataclass(frozen=True, slots=True)
class GrammarRuntimeEvent:
    """Append-only runtime event — future analytics source."""

    sequence: int
    event_type: GrammarRuntimeEventType
    lesson_id: str
    at: str
    step_id: str | None = None
    step_kind: GrammarLessonStepKind | None = None
    detail: str = ""


@dataclass(frozen=True, slots=True)
class GrammarEvidenceRequest:
    """Expected evidence request for a completed/eligible step (not a mastery write)."""

    step_id: str
    grammar_id: str
    observation_types_hint: tuple[str, ...] = ("formative",)
    context_hint: str | None = None
    skill: GrammarReinforcementSkill | None = None


@dataclass(frozen=True, slots=True)
class GrammarStepExecutionRecord:
    """Tracking record for one Skill Executor invocation (V1.1) — no analytics."""

    execution_id: str
    skill_executor_id: str
    activity_id: str
    step_id: str
    status: str
    lifecycle_phases: tuple[str, ...] = ()
    duration_ms: int = 0
    started_at: str = ""
    finished_at: str = ""
    evidence_observation_ids: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True, slots=True)
class GrammarRuntimeSession:
    """Persisted Grammar lesson runtime state under grammar.runtime JSONB."""

    student_id: int
    language_id: int
    grammar_id: str
    lesson_id: str
    state: GrammarRuntimeState
    cursor: GrammarRuntimeCursor
    blueprint_fingerprint: str
    completed_step_ids: tuple[str, ...] = ()
    pending_step_ids: tuple[str, ...] = ()
    events: tuple[GrammarRuntimeEvent, ...] = ()
    evidence_requests: tuple[GrammarEvidenceRequest, ...] = ()
    step_executions: tuple[GrammarStepExecutionRecord, ...] = ()
    package_id: str = ""
    failure_reason: str | None = None
    schema_version: int = GRAMMAR_RUNTIME_SCHEMA_VERSION
    enabled: bool = True

    @property
    def lifecycle(self) -> GrammarRuntimeLifecycle:
        """G0-compatible lifecycle projection."""
        return lifecycle_from_state(self.state)


@dataclass(frozen=True, slots=True)
class GrammarRuntimeView:
    """Public runtime output surface."""

    session: GrammarRuntimeSession
    current_state: GrammarRuntimeState
    completed_steps: tuple[str, ...]
    pending_steps: tuple[str, ...]
    events: tuple[GrammarRuntimeEvent, ...]
    expected_evidence_requests: tuple[GrammarEvidenceRequest, ...] = field(default_factory=tuple)


# Allowed deterministic transitions: from -> frozenset(to)
ALLOWED_TRANSITIONS: dict[GrammarRuntimeState, frozenset[GrammarRuntimeState]] = {
    GrammarRuntimeState.created: frozenset(
        {GrammarRuntimeState.ready, GrammarRuntimeState.cancelled, GrammarRuntimeState.failed}
    ),
    GrammarRuntimeState.ready: frozenset(
        {GrammarRuntimeState.running, GrammarRuntimeState.cancelled, GrammarRuntimeState.failed}
    ),
    GrammarRuntimeState.running: frozenset(
        {
            GrammarRuntimeState.step_completed,
            GrammarRuntimeState.paused,
            GrammarRuntimeState.cancelled,
            GrammarRuntimeState.failed,
        }
    ),
    GrammarRuntimeState.paused: frozenset(
        {GrammarRuntimeState.running, GrammarRuntimeState.cancelled, GrammarRuntimeState.failed}
    ),
    GrammarRuntimeState.step_completed: frozenset(
        {
            GrammarRuntimeState.running,
            GrammarRuntimeState.completed,
            GrammarRuntimeState.cancelled,
            GrammarRuntimeState.failed,
        }
    ),
    GrammarRuntimeState.completed: frozenset(),
    GrammarRuntimeState.failed: frozenset(),
    GrammarRuntimeState.cancelled: frozenset(),
}
