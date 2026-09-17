"""Generation Pipeline (W5) — orchestrate normalize → validate → repair → canonical lesson → audit.

Architecture only — no LLM calls, no runtime persistence.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing_generation.audit_types import GenerationOutcome, WritingGenerationAuditRecord
from app.services.language_writing_generation.canonical_lesson_types import (
    WritingCanonicalGeneratedLesson,
    canonical_lesson_fields_complete,
)
from app.services.language_writing_generation.generation_audit import (
    GENERATOR_PIPELINE_VERSION,
    build_generation_audit,
)
from app.services.language_writing_generation.generation_hash import compute_generation_hash
from app.services.language_writing_generation.lesson_validator import validate_lesson_draft
from app.services.language_writing_generation.normalizer_types import NormalizationResult, WritingLlmRawResponse
from app.services.language_writing_generation.prompt_builder_types import WritingPromptBundle
from app.services.language_writing_generation.repair_layer import repair_lesson_draft
from app.services.language_writing_generation.repair_types import RepairResult
from app.services.language_writing_generation.response_normalizer import normalize_llm_response
from app.services.language_writing_generation.validator_types import ValidationResult
from app.services.language_writing_lesson_planner.types import WritingLessonBlueprint


@dataclass(frozen=True, slots=True)
class GenerationPipelineResult:
    """Full pipeline outcome — canonical lesson + audit (may be partial on failure)."""

    success: bool
    outcome: GenerationOutcome
    canonical_lesson: WritingCanonicalGeneratedLesson | None
    normalization: NormalizationResult
    validation: ValidationResult | None
    repair: RepairResult | None
    audit: WritingGenerationAuditRecord
    pipeline_version: str = GENERATOR_PIPELINE_VERSION


def process_llm_generation(
    blueprint: WritingLessonBlueprint,
    _prompt_bundle: WritingPromptBundle,
    raw_llm_response: WritingLlmRawResponse,
    *,
    generation_duration_ms: int = 0,
    attempt_repair: bool = True,
) -> GenerationPipelineResult:
    """Run generation pipeline on raw LLM output — no LLM invocation in W5."""
    normalization = normalize_llm_response(raw_llm_response)

    if not normalization.success or normalization.draft is None:
        audit = build_generation_audit(
            blueprint=blueprint,
            lesson=None,
            normalization=normalization,
            validation=None,
            repair=None,
            llm_version=raw_llm_response.llm_version,
            generation_duration_ms=generation_duration_ms,
            outcome=GenerationOutcome.hard_failure,
        )
        return GenerationPipelineResult(
            success=False,
            outcome=GenerationOutcome.hard_failure,
            canonical_lesson=None,
            normalization=normalization,
            validation=None,
            repair=None,
            audit=audit,
        )

    draft = normalization.draft
    validation = validate_lesson_draft(draft, blueprint)
    repair: RepairResult | None = None

    if attempt_repair and (not validation.passed or validation.warning_count > 0):
        draft, repair = repair_lesson_draft(draft, blueprint, validation)
        validation = validate_lesson_draft(draft, blueprint)

    if not validation.passed:
        audit = build_generation_audit(
            blueprint=blueprint,
            lesson=None,
            normalization=normalization,
            validation=validation,
            repair=repair,
            llm_version=raw_llm_response.llm_version,
            generation_duration_ms=generation_duration_ms,
            outcome=GenerationOutcome.hard_failure,
        )
        return GenerationPipelineResult(
            success=False,
            outcome=GenerationOutcome.hard_failure,
            canonical_lesson=None,
            normalization=normalization,
            validation=validation,
            repair=repair,
            audit=audit,
        )

    outcome = GenerationOutcome.success
    if repair and repair.repaired:
        outcome = GenerationOutcome.soft_failure

    lesson_without_hash = WritingCanonicalGeneratedLesson.from_repaired_draft(
        draft,
        blueprint_id=blueprint.blueprint_id,
        blueprint_version=blueprint.blueprint_version,
        blueprint_schema_version=blueprint.schema_version,
        blueprint_hash=blueprint.blueprint_hash,
        generation_hash="",
        writing_minutes=blueprint.time_plan.writing_minutes,
        revision_minutes=blueprint.time_plan.revision_minutes,
        total_minutes=blueprint.time_plan.total_minutes,
    )
    generation_hash = compute_generation_hash(lesson_without_hash)
    canonical = WritingCanonicalGeneratedLesson.from_repaired_draft(
        draft,
        blueprint_id=blueprint.blueprint_id,
        blueprint_version=blueprint.blueprint_version,
        blueprint_schema_version=blueprint.schema_version,
        blueprint_hash=blueprint.blueprint_hash,
        generation_hash=generation_hash,
        writing_minutes=blueprint.time_plan.writing_minutes,
        revision_minutes=blueprint.time_plan.revision_minutes,
        total_minutes=blueprint.time_plan.total_minutes,
    )

    audit = build_generation_audit(
        blueprint=blueprint,
        lesson=canonical,
        normalization=normalization,
        validation=validation,
        repair=repair,
        llm_version=raw_llm_response.llm_version,
        generation_duration_ms=generation_duration_ms,
        outcome=outcome,
    )

    return GenerationPipelineResult(
        success=canonical_lesson_fields_complete(canonical),
        outcome=outcome,
        canonical_lesson=canonical,
        normalization=normalization,
        validation=validation,
        repair=repair,
        audit=audit,
    )
