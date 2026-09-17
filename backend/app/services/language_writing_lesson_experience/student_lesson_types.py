"""Student Lesson Experience types (W4) — everything visible to the student."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing_generation.mission_builder_types import WritingEstimatedTime, WritingStudentMission

STUDENT_LESSON_SCHEMA_VERSION = "4.0.0"


@dataclass(frozen=True, slots=True)
class WritingStudentLessonExperience:
    """Canonical student-visible lesson object (W4).

    Assembled from Mission Builder output. No coach, no grading, no journey fields.
    """

    mission_title: str
    writing_context: str
    instructions: tuple[str, ...]
    checklist: tuple[str, ...]
    learning_outcomes: tuple[str, ...]
    estimated_time: WritingEstimatedTime
    expected_output: str
    constraints: tuple[str, ...]
    success_criteria: tuple[str, ...]
    tips: tuple[str, ...]
    writing_prompt: str
    blueprint_id: str
    blueprint_version: str
    blueprint_schema_version: str
    blueprint_hash: str
    experience_schema_version: str = STUDENT_LESSON_SCHEMA_VERSION

    @staticmethod
    def from_mission(
        mission: WritingStudentMission,
        *,
        blueprint_schema_version: str,
    ) -> WritingStudentLessonExperience:
        return WritingStudentLessonExperience(
            mission_title=mission.mission_title,
            writing_context=mission.mission_context,
            instructions=mission.instructions,
            checklist=mission.checklist,
            learning_outcomes=mission.learning_outcomes,
            estimated_time=mission.estimated_time,
            expected_output=mission.expected_output,
            constraints=mission.constraints,
            success_criteria=mission.success_criteria,
            tips=mission.tips,
            writing_prompt=mission.writing_prompt,
            blueprint_id=mission.blueprint_id,
            blueprint_version=mission.blueprint_version,
            blueprint_schema_version=blueprint_schema_version,
            blueprint_hash=mission.blueprint_hash,
        )

    def to_student_dict(self) -> dict[str, object]:
        return {
            "mission_title": self.mission_title,
            "writing_context": self.writing_context,
            "instructions": list(self.instructions),
            "checklist": list(self.checklist),
            "learning_outcomes": list(self.learning_outcomes),
            "estimated_time": {
                "writing_minutes": self.estimated_time.writing_minutes,
                "revision_minutes": self.estimated_time.revision_minutes,
                "total_minutes": self.estimated_time.total_minutes,
            },
            "expected_output": self.expected_output,
            "constraints": list(self.constraints),
            "success_criteria": list(self.success_criteria),
            "tips": list(self.tips),
            "writing_prompt": self.writing_prompt,
            "blueprint_id": self.blueprint_id,
            "blueprint_version": self.blueprint_version,
            "blueprint_schema_version": self.blueprint_schema_version,
            "blueprint_hash": self.blueprint_hash,
            "experience_schema_version": self.experience_schema_version,
        }


def student_lesson_fields_complete(lesson: WritingStudentLessonExperience) -> bool:
    return bool(
        lesson.mission_title.strip()
        and lesson.writing_context.strip()
        and lesson.instructions
        and lesson.checklist
        and lesson.learning_outcomes
        and lesson.estimated_time.total_minutes > 0
        and lesson.expected_output
        and lesson.constraints
        and lesson.success_criteria
        and lesson.writing_prompt.strip()
        and lesson.blueprint_hash
    )
