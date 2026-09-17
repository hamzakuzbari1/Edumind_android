"""Mission Builder (W4) — assembles student-facing mission from blueprint only; no LLM."""

from __future__ import annotations

from app.services.language_writing_lesson_planner.types import WritingLessonBlueprint
from app.services.language_writing_generation.mission_builder_types import (
    MISSION_BUILDER_VERSION,
    WritingEstimatedTime,
    WritingStudentMission,
)


def _tips_from_blueprint(blueprint: WritingLessonBlueprint) -> tuple[str, ...]:
    tips: list[str] = []
    for driver in blueprint.difficulty_drivers[:2]:
        tips.append(f"Focus area: {driver}")
    for mistake in blueprint.common_mistakes[:2]:
        if ":" in mistake:
            _, desc = mistake.split(":", 1)
            tips.append(f"Avoid: {desc.strip()}")
        else:
            tips.append(f"Avoid: {mistake}")
    return tuple(tips[:4])


def build_mission_from_blueprint(blueprint: WritingLessonBlueprint) -> WritingStudentMission:
    """Assemble student mission from blueprint — never makes educational decisions."""
    title = f"{blueprint.goal_profile_label}: {blueprint.chain_node_id.replace('_', ' ').title()}"
    context = blueprint.narrative_why
    instructions = (
        f"Write a {blueprint.expected_writing_output.value} for this situation.",
        f"Use {blueprint.grammar_targets.primary.replace('_', ' ')} correctly.",
        f"Include vocabulary such as: {', '.join(blueprint.vocabulary_targets.primary[:4])}.",
        f"Complete the {blueprint.task_type.replace('_', ' ')} task in {blueprint.genre.replace('_', ' ')} format.",
    )
    constraints = (
        f"Length: {blueprint.success_criteria.min_words}–{blueprint.success_criteria.max_words} words",
        f"Output format: {blueprint.success_criteria.required_output_format.value}",
        f"Goal: {blueprint.personal_goal.value.replace('_', ' ')}",
    )
    if blueprint.time_plan.writing_minutes:
        constraints = constraints + (f"Suggested writing time: {blueprint.time_plan.writing_minutes} minutes",)

    return WritingStudentMission(
        mission_title=title,
        mission_context=context,
        instructions=instructions,
        constraints=constraints,
        success_criteria=blueprint.success_criteria_labels,
        estimated_time=WritingEstimatedTime(
            writing_minutes=blueprint.time_plan.writing_minutes,
            revision_minutes=blueprint.time_plan.revision_minutes,
            total_minutes=blueprint.time_plan.total_minutes,
        ),
        learning_outcomes=blueprint.learning_outcomes,
        tips=_tips_from_blueprint(blueprint),
        checklist=blueprint.success_criteria_labels,
        expected_output=blueprint.expected_writing_output.value,
        writing_prompt=blueprint.carry_forward_context or context,
        blueprint_id=blueprint.blueprint_id,
        blueprint_version=blueprint.blueprint_version,
        blueprint_hash=blueprint.blueprint_hash,
        builder_version=MISSION_BUILDER_VERSION,
    )
