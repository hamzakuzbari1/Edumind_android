"""Student Lesson Experience assembler (W4) — mission builder output to canonical student lesson."""

from __future__ import annotations

from app.services.language_writing_generation.generator_contract import WritingLessonBlueprint
from app.services.language_writing_generation.mission_builder import build_mission_from_blueprint
from app.services.language_writing_lesson_experience.student_lesson_types import WritingStudentLessonExperience


def assemble_student_lesson_experience(blueprint: WritingLessonBlueprint) -> WritingStudentLessonExperience:
    """Blueprint -> Mission Builder -> Student Lesson Experience (no LLM, no grading)."""
    mission = build_mission_from_blueprint(blueprint)
    return WritingStudentLessonExperience.from_mission(
        mission,
        blueprint_schema_version=blueprint.schema_version,
    )
