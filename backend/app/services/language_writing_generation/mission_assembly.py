"""Deterministic mission assembly (W3.1) — delegates to Mission Builder (W4)."""

from __future__ import annotations

from app.services.language_writing_generation.generator_contract import (
    WritingGeneratedLesson,
    WritingGeneratorInput,
    WritingMissionAssembly,
)
from app.services.language_writing_generation.mission_builder import build_mission_from_blueprint


def assemble_mission_from_blueprint(input_ctx: WritingGeneratorInput) -> WritingGeneratedLesson:
    """Legacy W3 entry point — delegates to W4 Mission Builder without duplicating logic."""
    bp = input_ctx.blueprint
    mission = build_mission_from_blueprint(bp)
    assembly = WritingMissionAssembly(
        mission_title=mission.mission_title,
        mission_summary=mission.mission_context,
        instructions=mission.instructions,
        writing_prompt=mission.writing_prompt,
        constraints=mission.constraints,
        expected_output_label=mission.expected_output,
        student_context=mission.mission_context,
        checklist=mission.checklist,
    )
    return WritingGeneratedLesson(
        assembly=assembly,
        blueprint_id=mission.blueprint_id,
        blueprint_version=mission.blueprint_version,
        blueprint_schema_version=bp.schema_version,
        blueprint_hash=mission.blueprint_hash,
        generator_version=input_ctx.generator_version,
        learning_outcomes=mission.learning_outcomes,
        success_criteria_labels=mission.success_criteria,
        grammar_primary=bp.grammar_targets.primary,
        vocabulary_primary=bp.vocabulary_targets.primary,
        expected_writing_output=mission.expected_output,
        personal_goal=bp.personal_goal.value,
    )
