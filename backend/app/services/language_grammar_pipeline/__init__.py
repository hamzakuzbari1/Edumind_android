"""Grammar Learning Pipeline (Integration Phase 1).

RESPONSIBILITY: Orchestrate existing Grammar Engine packages end-to-end.
No educational algorithms. No Runtime/Frontend/STT/TTS ownership.
"""

from __future__ import annotations

from app.services.language_grammar_pipeline.errors import (
    GrammarPipelineError,
    PipelineDisabledError,
    PipelineStageError,
    PipelineValidationError,
)
from app.services.language_grammar_pipeline.fingerprint import (
    fingerprint_pipeline_request,
    fingerprint_replay_bundle,
)
from app.services.language_grammar_pipeline.flags import (
    grammar_engine_enabled,
    grammar_pipeline_enabled,
    grammar_pipeline_strict,
)
from app.services.language_grammar_pipeline.completion import (
    ActivityCompletionRequest,
    ActivityCompletionResult,
    apply_activity_completion_async,
    build_completion_observation,
)
from app.services.language_grammar_pipeline.generate import (
    generate_grammar_lesson,
    lesson_dict_from_generation,
)
from app.services.language_grammar_pipeline.pipeline import (
    GrammarLearningPipeline,
    run_grammar_learning_pipeline,
)
from app.services.language_grammar_pipeline.store import (
    get_replay_bundle,
    reset_replay_store_for_tests,
    save_replay_bundle,
)
from app.services.language_grammar_pipeline.transactions import (
    abort_before_writes,
    mark_evaluation_succeeded,
    mark_evidence_ready,
    mark_mastery_applied,
    mark_progression_synced,
    mark_review_applied,
)
from app.services.language_grammar_pipeline.types import (
    GRAMMAR_PIPELINE_PACKAGE_VERSION,
    GRAMMAR_PIPELINE_SCHEMA_VERSION,
    PipelineEvent,
    PipelineEventType,
    PipelineMode,
    PipelineObservability,
    PipelineOutcome,
    PipelineReplayBundle,
    PipelineRequest,
    PipelineStage,
    PipelineStageFailure,
    PipelineStatus,
    WriteGate,
)

PACKAGE_VERSION = GRAMMAR_PIPELINE_PACKAGE_VERSION
RESPONSIBILITY = (
    "Grammar Learning Pipeline — orchestrate Progression→Planner→Authoring→Execute→"
    "Evaluate→Evidence→Mastery→Review→Recommend; Wave B durable completion writes "
    "via apply_activity_completion_async only; no educational algorithms"
)

__all__ = [
    "ActivityCompletionRequest",
    "ActivityCompletionResult",
    "GRAMMAR_PIPELINE_PACKAGE_VERSION",
    "GRAMMAR_PIPELINE_SCHEMA_VERSION",
    "PACKAGE_VERSION",
    "RESPONSIBILITY",
    "GrammarLearningPipeline",
    "GrammarPipelineError",
    "PipelineDisabledError",
    "PipelineEvent",
    "PipelineEventType",
    "PipelineMode",
    "PipelineObservability",
    "PipelineOutcome",
    "PipelineReplayBundle",
    "PipelineRequest",
    "PipelineStage",
    "PipelineStageError",
    "PipelineStageFailure",
    "PipelineStatus",
    "PipelineValidationError",
    "WriteGate",
    "abort_before_writes",
    "apply_activity_completion_async",
    "build_completion_observation",
    "fingerprint_pipeline_request",
    "fingerprint_replay_bundle",
    "generate_grammar_lesson",
    "get_replay_bundle",
    "grammar_engine_enabled",
    "grammar_pipeline_enabled",
    "grammar_pipeline_strict",
    "lesson_dict_from_generation",
    "mark_evaluation_succeeded",
    "mark_evidence_ready",
    "mark_mastery_applied",
    "mark_progression_synced",
    "mark_review_applied",
    "reset_replay_store_for_tests",
    "run_grammar_learning_pipeline",
    "save_replay_bundle",
]
