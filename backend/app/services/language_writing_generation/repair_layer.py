"""Repair Layer (W5) — structural repairs from blueprint/mission; no educational invention."""

from __future__ import annotations

from app.services.language_writing.enums import ExpectedWritingOutput
from app.services.language_writing_generation.mission_builder import build_mission_from_blueprint
from app.services.language_writing_generation.normalizer_types import WritingNormalizedLessonDraft
from app.services.language_writing_generation.repair_types import (
    REPAIR_LAYER_VERSION,
    RepairAction,
    RepairActionCode,
    RepairResult,
)
from app.services.language_writing_generation.validator_types import ValidationIssueCode, ValidationResult
from app.services.language_writing_lesson_planner.types import WritingLessonBlueprint


def _normalize_expected_output(value: str, blueprint: WritingLessonBlueprint) -> tuple[str, RepairAction | None]:
    if not value:
        return blueprint.expected_writing_output.value, RepairAction(
            code=RepairActionCode.restore_expected_output_from_blueprint,
            field="expected_output",
            detail="Restored from blueprint",
        )
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    for member in ExpectedWritingOutput:
        if member.value.lower() == normalized or member.name.lower() == normalized:
            if member.value != value:
                return member.value, RepairAction(
                    code=RepairActionCode.normalize_enum_casing,
                    field="expected_output",
                    detail=f"Normalized '{value}' -> '{member.value}'",
                )
            return member.value, None
    return blueprint.expected_writing_output.value, RepairAction(
        code=RepairActionCode.restore_expected_output_from_blueprint,
        field="expected_output",
        detail=f"Unknown value '{value}' — restored from blueprint",
    )


def repair_lesson_draft(
    draft: WritingNormalizedLessonDraft,
    blueprint: WritingLessonBlueprint,
    validation: ValidationResult | None = None,
) -> tuple[WritingNormalizedLessonDraft, RepairResult]:
    """Apply structural repairs — copy missing fields from blueprint/mission only."""
    mission = build_mission_from_blueprint(blueprint)
    actions: list[RepairAction] = []
    issue_codes = {issue.code for issue in validation.issues} if validation else set()

    checklist = draft.checklist
    if not checklist:
        checklist = mission.checklist
        actions.append(
            RepairAction(
                code=RepairActionCode.restore_checklist_from_blueprint,
                field="checklist",
                detail="Restored from blueprint success_criteria_labels",
            )
        )

    tips = draft.tips
    if not tips:
        tips = mission.tips
        actions.append(
            RepairAction(
                code=RepairActionCode.restore_tips_from_mission,
                field="tips",
                detail="Restored from mission builder tips",
            )
        )

    learning_outcomes = draft.learning_outcomes
    if not learning_outcomes:
        learning_outcomes = blueprint.learning_outcomes
        actions.append(
            RepairAction(
                code=RepairActionCode.restore_learning_outcomes_from_blueprint,
                field="learning_outcomes",
                detail="Restored from blueprint",
            )
        )

    success_criteria = draft.success_criteria
    if not success_criteria:
        success_criteria = blueprint.success_criteria_labels
        actions.append(
            RepairAction(
                code=RepairActionCode.restore_success_criteria_from_blueprint,
                field="success_criteria",
                detail="Restored from blueprint",
            )
        )

    constraints = draft.constraints
    if not constraints:
        constraints = mission.constraints
        actions.append(
            RepairAction(
                code=RepairActionCode.restore_constraints_from_mission,
                field="constraints",
                detail="Restored from mission builder",
            )
        )

    expected_output, expected_action = _normalize_expected_output(draft.expected_output, blueprint)
    if expected_action:
        actions.append(expected_action)

    grammar_display = draft.grammar_display
    if not grammar_display or ValidationIssueCode.grammar_metadata_mismatch in issue_codes:
        grammar_display = blueprint.grammar_targets.primary.replace("_", " ")
        actions.append(
            RepairAction(
                code=RepairActionCode.restore_grammar_display_from_blueprint,
                field="grammar_display",
                detail="Restored primary grammar from blueprint",
            )
        )

    vocabulary_display = draft.vocabulary_display
    if not vocabulary_display or ValidationIssueCode.vocabulary_metadata_mismatch in issue_codes:
        vocabulary_display = ", ".join(blueprint.vocabulary_targets.primary[:6])
        actions.append(
            RepairAction(
                code=RepairActionCode.restore_vocabulary_display_from_blueprint,
                field="vocabulary_display",
                detail="Restored primary vocabulary from blueprint",
            )
        )

    instructions = draft.instructions
    if not instructions:
        instructions = mission.instructions
        actions.append(
            RepairAction(
                code=RepairActionCode.fill_empty_optional_array,
                field="instructions",
                detail="Restored from mission builder",
            )
        )

    repaired_draft = WritingNormalizedLessonDraft(
        mission_title=draft.mission_title or mission.mission_title,
        writing_context=draft.writing_context or mission.mission_context,
        instructions=instructions,
        writing_prompt=draft.writing_prompt or mission.writing_prompt,
        constraints=constraints,
        checklist=checklist,
        tips=tips,
        learning_outcomes=learning_outcomes,
        success_criteria=success_criteria,
        expected_output=expected_output,
        grammar_display=grammar_display,
        vocabulary_display=vocabulary_display,
        estimated_time_minutes=draft.estimated_time_minutes or mission.estimated_time.total_minutes,
        unknown_fields=draft.unknown_fields,
    )

    return repaired_draft, RepairResult(
        repaired=len(actions) > 0,
        actions=tuple(actions),
        repair_layer_version=REPAIR_LAYER_VERSION,
    )
