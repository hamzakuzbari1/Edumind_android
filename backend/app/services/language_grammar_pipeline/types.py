"""Grammar Learning Pipeline contracts (Integration Phase 1).

Orchestration envelopes only — no educational algorithms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.services.language_grammar_activity_authoring.adaptive import StudentLearningSnapshot
from app.services.language_grammar_activity_spec import ActivitySpecification
from app.services.language_grammar_evaluation.types import GrammarEvaluationResult
from app.services.language_grammar_evidence.types import GrammarEvidenceBatch, GrammarEvidenceObservation
from app.services.language_grammar_integration.types import (
    GrammarCompletedSyncResult,
    GrammarLearningSnapshot,
    GrammarResolveTargetsResult,
)
from app.services.language_grammar_lesson_planner.types import GrammarLessonBlueprint
from app.services.language_grammar_mastery.types import GrammarMasterySnapshot
from app.services.language_grammar_progression.types import GrammarProgressionSnapshot
from app.services.language_grammar_review.types import GrammarReviewSnapshot
from app.services.language_grammar_skill_executor.types import ExecutionResult

GRAMMAR_PIPELINE_SCHEMA_VERSION = 1
GRAMMAR_PIPELINE_PACKAGE_VERSION = "1.0.0"


class PipelineMode(str, Enum):
    run = "run"
    replay = "replay"


class PipelineStatus(str, Enum):
    completed = "completed"
    failed = "failed"
    disabled = "disabled"
    aborted = "aborted"


class PipelineStage(str, Enum):
    resolve = "resolve"
    plan = "plan"
    author = "author"
    execute = "execute"
    evaluate = "evaluate"
    evidence = "evidence"
    mastery = "mastery"
    review = "review"
    recommend = "recommend"


class PipelineEventType(str, Enum):
    GrammarLessonStarted = "GrammarLessonStarted"
    LessonGenerated = "LessonGenerated"
    LessonExecuted = "LessonExecuted"
    GrammarEvaluated = "GrammarEvaluated"
    EvidenceProduced = "EvidenceProduced"
    MasteryUpdated = "MasteryUpdated"
    ReviewUpdated = "ReviewUpdated"
    LessonCompleted = "LessonCompleted"
    PipelineFailed = "PipelineFailed"
    PipelineDisabled = "PipelineDisabled"
    StageStarted = "StageStarted"
    StageCompleted = "StageCompleted"
    StageFailed = "StageFailed"


@dataclass(frozen=True, slots=True)
class PipelineEvent:
    sequence: int
    event_type: PipelineEventType
    pipeline_id: str
    stage: str = ""
    at: str = ""
    detail: str = ""


@dataclass(frozen=True, slots=True)
class PipelineStageFailure:
    stage: PipelineStage
    code: str
    message: str
    recoverable: bool = True


@dataclass(frozen=True, slots=True)
class PipelineObservability:
    pipeline_id: str
    lesson_id: str = ""
    grammar_target: str = ""
    activity_id: str = ""
    execution_id: str = ""
    evaluation_id: str = ""
    mastery_version: str = ""
    review_version: str = ""
    duration_ms: float = 0.0
    mode: str = PipelineMode.run.value


@dataclass(frozen=True, slots=True)
class PipelineReplayBundle:
    """Stored artifacts for deterministic replay — no LLM regeneration."""

    pipeline_id: str
    blueprint: GrammarLessonBlueprint
    specification: ActivitySpecification
    student_response: str
    grammar_targets: tuple[str, ...] = ()
    expected_patterns: tuple[str, ...] = ()
    evaluation_result: GrammarEvaluationResult | None = None
    evidence_batch: GrammarEvidenceBatch | None = None
    execution_result: ExecutionResult | None = None
    execution_session_id: str = ""
    as_of: str = ""


@dataclass(frozen=True, slots=True)
class WriteGate:
    """Transaction boundary — mastery/review/progression writes require evaluation OK."""

    evaluation_succeeded: bool = False
    evidence_ready: bool = False
    mastery_applied: bool = False
    review_applied: bool = False
    progression_synced: bool = False
    aborted: bool = False
    abort_reason: str = ""

    def may_write_mastery(self) -> bool:
        return self.evaluation_succeeded and self.evidence_ready and not self.aborted

    def may_write_review(self) -> bool:
        return self.may_write_mastery() and self.mastery_applied and not self.aborted

    def may_sync_progression(self) -> bool:
        return self.may_write_review() and self.review_applied and not self.aborted


@dataclass(frozen=True, slots=True)
class PipelineRequest:
    """Constrained pipeline input — orchestration only."""

    student_id: int
    language_id: int
    student_response: str
    learning_snapshot: GrammarLearningSnapshot | None = None
    blueprint: GrammarLessonBlueprint | None = None
    specification: ActivitySpecification | None = None
    expected_patterns: tuple[str, ...] = ()
    adaptive_snapshot: StudentLearningSnapshot | None = None
    prior_mastery: GrammarMasterySnapshot | None = None
    prior_progression: GrammarProgressionSnapshot | None = None
    use_llm_authoring: bool = False
    activity_type: str = "voice_recording"
    as_of: str = ""
    pipeline_id: str = ""
    mode: PipelineMode = PipelineMode.run
    replay_bundle: PipelineReplayBundle | None = None
    apply_learner_writes: bool = True
    localization: str = "en"
    overall_cefr: str = "A2"
    source_skill: str = "speaking"


@dataclass(frozen=True, slots=True)
class PipelineOutcome:
    """End-to-end learning outcome — evidence of orchestration, not new pedagogy."""

    status: PipelineStatus
    observability: PipelineObservability
    write_gate: WriteGate
    events: tuple[PipelineEvent, ...] = ()
    failures: tuple[PipelineStageFailure, ...] = ()
    grammar_targets: tuple[str, ...] = ()
    blueprint: GrammarLessonBlueprint | None = None
    specification: ActivitySpecification | None = None
    execution_result: ExecutionResult | None = None
    execution_session_id: str = ""
    evaluation_result: GrammarEvaluationResult | None = None
    evidence_batch: GrammarEvidenceBatch | None = None
    observations: tuple[GrammarEvidenceObservation, ...] = ()
    mastery_snapshot: GrammarMasterySnapshot | None = None
    review_snapshot: GrammarReviewSnapshot | None = None
    completed_sync: GrammarCompletedSyncResult | None = None
    next_recommendation: GrammarResolveTargetsResult | None = None
    replay_bundle: PipelineReplayBundle | None = None
    pipeline_version: str = GRAMMAR_PIPELINE_PACKAGE_VERSION
    notes: str = ""
    llm_authoring_invoked: bool = False
    authoring_invoked: bool = False
    execution_invoked: bool = False


@dataclass
class PipelineEventLog:
    """Mutable event collector used only inside the orchestrator."""

    pipeline_id: str
    events: list[PipelineEvent] = field(default_factory=list)

    def emit(
        self,
        event_type: PipelineEventType,
        *,
        stage: str = "",
        at: str = "",
        detail: str = "",
    ) -> PipelineEvent:
        event = PipelineEvent(
            sequence=len(self.events) + 1,
            event_type=event_type,
            pipeline_id=self.pipeline_id,
            stage=stage,
            at=at,
            detail=detail,
        )
        self.events.append(event)
        return event
