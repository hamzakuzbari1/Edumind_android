"""Writing Generation (W3.1/W4/W5) — Mission Builder through Generation Audit; no LLM in W5."""

from __future__ import annotations

from app.services.language_writing_generation.audit_types import (
    GENERATION_AUDIT_VERSION,
    GenerationOutcome,
    WritingGenerationAuditRecord,
)
from app.services.language_writing_generation.canonical_lesson_types import (
    CANONICAL_LESSON_SCHEMA_VERSION,
    WritingCanonicalGeneratedLesson,
    canonical_lesson_fields_complete,
)
from app.services.language_writing_generation.failure_strategy import (
    DEFAULT_FAILURE_STRATEGY,
    FAILURE_STRATEGY_VERSION,
    FailureStrategyPolicy,
)
from app.services.language_writing_generation.generation_audit import (
    GENERATOR_PIPELINE_VERSION,
    build_generation_audit,
)
from app.services.language_writing_generation.generation_hash import (
    GENERATION_HASH_VERSION,
    compute_generation_hash,
)
from app.services.language_writing_generation.generation_pipeline import (
    GenerationPipelineResult,
    process_llm_generation,
)
from app.services.language_writing_generation.lesson_validator import validate_lesson_draft
from app.services.language_writing_generation.mission_builder import build_mission_from_blueprint
from app.services.language_writing_generation.mission_builder_types import (
    MISSION_BUILDER_VERSION,
    WritingEstimatedTime,
    WritingStudentMission,
    mission_fields_complete,
)
from app.services.language_writing_generation.normalizer_types import (
    NORMALIZER_VERSION,
    NormalizationResult,
    WritingLlmRawResponse,
    WritingNormalizedLessonDraft,
)
from app.services.language_writing_generation.prompt_builder import build_prompt_from_blueprint
from app.services.language_writing_generation.prompt_builder_types import (
    LLM_FORBIDDEN_DIRECT_ACCESS,
    PROMPT_BUILDER_VERSION,
    PROMPT_FORBIDDEN_CONTEXT_SOURCES,
    PromptSectionKey,
    WritingPromptBundle,
    WritingPromptSection,
)
from app.services.language_writing_generation.repair_layer import repair_lesson_draft
from app.services.language_writing_generation.repair_types import (
    FORBIDDEN_REPAIR_ACTIONS,
    REPAIR_LAYER_VERSION,
    RepairResult,
)
from app.services.language_writing_generation.response_normalizer import normalize_llm_response
from app.services.language_writing_generation.validator_types import (
    VALIDATOR_VERSION,
    ValidationResult,
)

PACKAGE_VERSION = "5.0.0"
ARCHITECTURE_VERSION = "5.0.0"
RESPONSIBILITY = (
    "Writing generation pipeline — Mission Builder, Prompt Builder, Normalizer, "
    "Validator, Repair, Canonical Lesson, Generation Audit (no LLM calls in W5)"
)

# Canonical body_json keys for writing lessons
WRITING_CURRICULUM_KEY = "writing_curriculum"
WRITING_GOAL_KEY = "writing_goal"
WRITING_COACH_KEY = "writing_coach"
WRITING_CHALLENGE_KEY = "writing_challenge"
WRITING_GENERATION_KEY = "writing_generation"
WRITING_BLUEPRINT_KEY = "writing_blueprint"

__all__ = [
    "ARCHITECTURE_VERSION",
    "CANONICAL_LESSON_SCHEMA_VERSION",
    "DEFAULT_FAILURE_STRATEGY",
    "FAILURE_STRATEGY_VERSION",
    "FORBIDDEN_REPAIR_ACTIONS",
    "GENERATION_AUDIT_VERSION",
    "GENERATION_HASH_VERSION",
    "GENERATOR_PIPELINE_VERSION",
    "GenerationOutcome",
    "GenerationPipelineResult",
    "LLM_FORBIDDEN_DIRECT_ACCESS",
    "MISSION_BUILDER_VERSION",
    "NORMALIZER_VERSION",
    "PACKAGE_VERSION",
    "PROMPT_BUILDER_VERSION",
    "PROMPT_FORBIDDEN_CONTEXT_SOURCES",
    "PromptSectionKey",
    "REPAIR_LAYER_VERSION",
    "RESPONSIBILITY",
    "VALIDATOR_VERSION",
    "WRITING_BLUEPRINT_KEY",
    "WRITING_CHALLENGE_KEY",
    "WRITING_COACH_KEY",
    "WRITING_CURRICULUM_KEY",
    "WRITING_GENERATION_KEY",
    "WRITING_GOAL_KEY",
    "FailureStrategyPolicy",
    "NormalizationResult",
    "RepairResult",
    "ValidationResult",
    "WritingCanonicalGeneratedLesson",
    "WritingEstimatedTime",
    "WritingGenerationAuditRecord",
    "WritingLlmRawResponse",
    "WritingNormalizedLessonDraft",
    "WritingPromptBundle",
    "WritingPromptSection",
    "WritingStudentMission",
    "build_generation_audit",
    "build_mission_from_blueprint",
    "build_prompt_from_blueprint",
    "canonical_lesson_fields_complete",
    "compute_generation_hash",
    "mission_fields_complete",
    "normalize_llm_response",
    "process_llm_generation",
    "repair_lesson_draft",
    "validate_lesson_draft",
]
