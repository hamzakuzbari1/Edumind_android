"""Skill Execution Framework contracts (G3.4).

Executors receive ActivitySpecification + ExecutionContext only.
They return ExecutionResult only — never Progression / Mastery / Review writes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, runtime_checkable

from app.services.language_grammar_activity_spec import ActivitySpecification
from app.services.language_grammar_evidence.types import GrammarEvidenceObservation

GRAMMAR_SKILL_EXECUTOR_SCHEMA_VERSION = 1
GRAMMAR_SKILL_EXECUTOR_PACKAGE_VERSION = "1.0.0"


class ExecutionStatus(StrEnum):
    pending = "pending"
    initialized = "initialized"
    prepared = "prepared"
    validated = "validated"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class CompletionState(StrEnum):
    incomplete = "incomplete"
    partial = "partial"
    complete = "complete"
    not_applicable = "not_applicable"


class LifecyclePhase(StrEnum):
    """Deterministic executor lifecycle phases (G3.4)."""

    initialize = "initialize"
    prepare = "prepare"
    validate = "validate"
    execute = "execute"
    complete = "complete"
    cancel = "cancel"
    cleanup = "cleanup"


LIFECYCLE_PHASES: tuple[LifecyclePhase, ...] = (
    LifecyclePhase.initialize,
    LifecyclePhase.prepare,
    LifecyclePhase.validate,
    LifecyclePhase.execute,
    LifecyclePhase.complete,
    LifecyclePhase.cancel,
    LifecyclePhase.cleanup,
)


@dataclass(frozen=True, slots=True)
class StudentContext:
    """Minimal student surface — no mastery / progression engines."""

    student_id: int
    language_id: int
    overall_cefr: str = ""
    locale: str = "en"


@dataclass(frozen=True, slots=True)
class TeacherPersona:
    """Opaque teacher surface for execution — no authoring / LLM prompts."""

    teacher_id: str = "default_tutor"
    persona_id: str = "default_tutor"
    tone: str = "supportive"
    extras: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionMetadata:
    """Opaque execution provenance — never engine internals."""

    as_of: str = ""
    attempt_index: int = 0
    preferred_executor_id: str = ""
    extras: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionFeatureFlags:
    """Flag snapshot passed into context — no Settings object leakage."""

    grammar_engine_enabled: bool = False
    skill_executor_enabled: bool = False
    skill_executor_strict: bool = True


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Canonical executor input (plus ActivitySpecification).

    No Runtime session objects, Planner blueprints, or Provider internals.
    No Grammar/Progression/Mastery/Review/Authoring logic.
    """

    specification: ActivitySpecification
    student: StudentContext
    runtime_session_id: str
    blueprint_id: str
    execution_id: str
    localization: str = "en"
    teacher_persona: TeacherPersona = field(default_factory=TeacherPersona)
    feature_flags: ExecutionFeatureFlags = field(default_factory=ExecutionFeatureFlags)
    metadata: ExecutionMetadata = field(default_factory=ExecutionMetadata)


@dataclass(frozen=True, slots=True)
class ExecutionTiming:
    """Deterministic timing markers (ISO strings or empty)."""

    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0


@dataclass(frozen=True, slots=True)
class ExecutorMetadata:
    """Opaque executor provenance on the result."""

    executor_id: str = ""
    executor_version: str = GRAMMAR_SKILL_EXECUTOR_PACKAGE_VERSION
    lifecycle_phases_completed: tuple[str, ...] = ()
    extras: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CollectedOutput:
    """One learner output channel collected during execution (placeholder-safe)."""

    output_id: str
    output_type: str
    value: str = ""
    present: bool = False


@dataclass(frozen=True, slots=True)
class ExecutionArtifact:
    """Opaque artifact reference — never a UI tree."""

    artifact_id: str
    kind: str = "placeholder"
    uri: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Canonical executor output — sole return contract (G3.4 + V1.5 fields)."""

    execution_id: str
    status: ExecutionStatus
    completion_state: CompletionState = CompletionState.incomplete
    artifacts: tuple[ExecutionArtifact, ...] = ()
    collected_outputs: tuple[CollectedOutput, ...] = ()
    generated_evidence: tuple[GrammarEvidenceObservation, ...] = ()
    warnings: tuple[str, ...] = ()
    timing: ExecutionTiming = field(default_factory=ExecutionTiming)
    executor_metadata: ExecutorMetadata = field(default_factory=ExecutorMetadata)
    notes: str = ""
    # V1.5 explicit result surface (interaction only — never mastery/CEFR).
    completion_status: str = ""
    completion_reason: str = ""
    student_response: str = ""
    metrics: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class SkillExecutor(Protocol):
    """Skill Executor interface — Runtime discovers via Registry only."""

    @property
    def executor_id(self) -> str: ...

    @property
    def supported_activity_types(self) -> frozenset[str]: ...

    def supports(self, activity_type: str) -> bool:
        """Whether this executor can run the given ActivitySpecification.activity_type."""
        ...

    def initialize(self, context: ExecutionContext) -> None: ...

    def prepare(self, context: ExecutionContext) -> None: ...

    def validate(self, context: ExecutionContext) -> None: ...

    def execute(self, context: ExecutionContext) -> ExecutionResult: ...

    def complete(self, context: ExecutionContext, result: ExecutionResult) -> ExecutionResult: ...

    def cancel(self, context: ExecutionContext, reason: str = "") -> ExecutionResult: ...

    def cleanup(self, context: ExecutionContext) -> None: ...
