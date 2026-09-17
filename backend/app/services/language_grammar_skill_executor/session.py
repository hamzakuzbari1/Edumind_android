"""Execution Session contracts (V1.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.services.language_grammar_activity_spec import ActivitySpecification
from app.services.language_grammar_evidence.types import GrammarEvidenceObservation
from app.services.language_grammar_skill_executor.types import (
    ExecutionContext,
    ExecutionResult,
)


class SessionStatus(StrEnum):
    """V1.5 execution session states — deterministic transitions only."""

    created = "created"
    initializing = "initializing"
    running = "running"
    waiting_for_student = "waiting_for_student"
    evaluating = "evaluating"
    completed = "completed"
    cancelled = "cancelled"
    failed = "failed"


class ExecutionLifecycleEventType(StrEnum):
    execution_created = "ExecutionCreated"
    execution_started = "ExecutionStarted"
    student_responded = "StudentResponded"
    evaluation_completed = "EvaluationCompleted"
    execution_completed = "ExecutionCompleted"
    execution_cancelled = "ExecutionCancelled"
    execution_failed = "ExecutionFailed"


TERMINAL_SESSION_STATUSES: frozenset[SessionStatus] = frozenset(
    {
        SessionStatus.completed,
        SessionStatus.cancelled,
        SessionStatus.failed,
    }
)


@dataclass(frozen=True, slots=True)
class ExecutionLifecycleEvent:
    sequence: int
    event_type: ExecutionLifecycleEventType
    execution_session_id: str
    at: str = ""
    detail: str = ""
    from_status: str = ""
    to_status: str = ""


@dataclass(frozen=True, slots=True)
class ExecutionSession:
    """Durable execution session — interaction ownership only."""

    execution_session_id: str
    execution_attempt_id: str
    activity_id: str
    activity_type: str
    student_id: int
    teacher_id: str
    grammar_targets: tuple[str, ...]
    status: SessionStatus
    started_at: str = ""
    completed_at: str = ""
    executor_id: str = ""
    localization: str = "en"
    student_response: str = ""
    schema_version: int = 1


@dataclass
class ExecutionEngineState:
    """Mutable engine envelope for lifecycle + replay snapshots."""

    session: ExecutionSession
    context: ExecutionContext
    specification: ActivitySpecification
    events: list[ExecutionLifecycleEvent] = field(default_factory=list)
    result: ExecutionResult | None = None
    observations: tuple[GrammarEvidenceObservation, ...] = ()
    status_history: list[str] = field(default_factory=list)
    snapshot_version: int = 1

    def view(self) -> dict[str, object]:
        """Serializable replay view — no mastery / progression fields."""
        return {
            "execution_session_id": self.session.execution_session_id,
            "execution_attempt_id": self.session.execution_attempt_id,
            "activity_id": self.session.activity_id,
            "activity_type": self.session.activity_type,
            "student_id": self.session.student_id,
            "teacher_id": self.session.teacher_id,
            "grammar_targets": list(self.session.grammar_targets),
            "status": self.session.status.value,
            "started_at": self.session.started_at,
            "completed_at": self.session.completed_at,
            "executor_id": self.session.executor_id,
            "localization": self.session.localization,
            "student_response": self.session.student_response,
            "status_history": list(self.status_history),
            "events": [
                {
                    "sequence": e.sequence,
                    "event_type": e.event_type.value,
                    "at": e.at,
                    "detail": e.detail,
                    "from_status": e.from_status,
                    "to_status": e.to_status,
                }
                for e in self.events
            ],
            "has_result": self.result is not None,
            "observation_count": len(self.observations),
            "observation_ids": [o.observation_id for o in self.observations],
            "snapshot_version": self.snapshot_version,
        }
