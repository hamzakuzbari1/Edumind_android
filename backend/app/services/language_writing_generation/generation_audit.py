"""Generation Audit (W5) — assemble audit record from pipeline results."""

from __future__ import annotations

from app.services.language_writing_generation.audit_types import (
    GENERATION_AUDIT_VERSION,
    GenerationOutcome,
    WritingGenerationAuditRecord,
)
from app.services.language_writing_generation.canonical_lesson_types import WritingCanonicalGeneratedLesson
from app.services.language_writing_generation.normalizer_types import NORMALIZER_VERSION, NormalizationResult
from app.services.language_writing_generation.prompt_builder_types import PROMPT_BUILDER_VERSION
from app.services.language_writing_generation.repair_types import REPAIR_LAYER_VERSION, RepairResult
from app.services.language_writing_generation.validator_types import VALIDATOR_VERSION, ValidationResult
from app.services.language_writing_lesson_planner.types import WritingLessonBlueprint

GENERATOR_PIPELINE_VERSION = "5.0.0"


def build_generation_audit(
    *,
    blueprint: WritingLessonBlueprint,
    lesson: WritingCanonicalGeneratedLesson | None,
    normalization: NormalizationResult,
    validation: ValidationResult | None,
    repair: RepairResult | None,
    llm_version: str,
    generation_duration_ms: int,
    outcome: GenerationOutcome,
) -> WritingGenerationAuditRecord:
    """Assemble audit metadata — architecture contract for future persistence."""
    return WritingGenerationAuditRecord(
        blueprint_version=blueprint.blueprint_version,
        blueprint_schema_version=blueprint.schema_version,
        blueprint_hash=blueprint.blueprint_hash,
        prompt_version=PROMPT_BUILDER_VERSION,
        generator_version=GENERATOR_PIPELINE_VERSION,
        llm_version=llm_version,
        generation_hash=lesson.generation_hash if lesson else "",
        generation_duration_ms=generation_duration_ms,
        validation_passed=validation.passed if validation else False,
        validation_error_count=validation.error_count if validation else 0,
        validation_warning_count=validation.warning_count if validation else 0,
        repair_applied=repair.repaired if repair else False,
        repair_action_count=len(repair.actions) if repair else 0,
        outcome=outcome,
        normalizer_version=normalization.normalizer_version or NORMALIZER_VERSION,
        validator_version=validation.validator_version if validation else VALIDATOR_VERSION,
        repair_layer_version=repair.repair_layer_version if repair else REPAIR_LAYER_VERSION,
        audit_version=GENERATION_AUDIT_VERSION,
    )
