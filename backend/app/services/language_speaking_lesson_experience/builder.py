"""Assemble the student-safe speaking lesson bundle from a blueprint (S10)."""

from __future__ import annotations

from app.services.language_speaking.enums import SpeakingExecutionMode
from app.services.language_speaking_lesson_experience.types import (
    LANGUAGE_SPEAKING_LESSON_EXPERIENCE_VERSION,
    SpeakingLessonExperienceBundle,
    SpeakingLessonExperienceMissionItem,
)
from app.services.language_speaking_lesson_planner.types import SpeakingLessonBlueprint


def build_lesson_experience_bundle(
    blueprint: SpeakingLessonBlueprint,
    *,
    current_focus_label: str = "",
) -> SpeakingLessonExperienceBundle:
    """Project a blueprint's educational missions into a student-safe bundle.

    Only learner-facing content is exposed: no scoring, gating, mastery, evidence
    intent, or raw skill IDs. Teaching blocks are included via their student dict.
    """
    items: list[SpeakingLessonExperienceMissionItem] = []
    for mission in sorted(blueprint.educational_missions, key=lambda m: m.order_index):
        items.append(
            SpeakingLessonExperienceMissionItem(
                mission_id=mission.mission_id,
                kind=mission.mission_kind.value,
                execution_mode=mission.execution_mode.value,
                order_index=mission.order_index,
                title=mission.title,
                learner_instructions=mission.learner_instructions,
                is_live=mission.execution_mode is SpeakingExecutionMode.live_evi_conversation,
                is_executable=mission.is_executable,
                objectives=tuple(o.student_objective_text for o in mission.objectives),
                teaching_blocks=tuple(b.to_student_dict() for b in mission.teaching_blocks),
                tasks=tuple(t.to_student_dict() for t in mission.tasks),
            )
        )
    return SpeakingLessonExperienceBundle(
        version=LANGUAGE_SPEAKING_LESSON_EXPERIENCE_VERSION,
        blueprint_id=blueprint.blueprint_id,
        session_goal=blueprint.session_goal,
        current_focus_label=current_focus_label or blueprint.alex_context.target_skill_label,
        missions=tuple(items),
    )
