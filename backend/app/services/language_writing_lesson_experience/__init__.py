"""Writing Lesson Experience (W0/W4) — Student Lesson Experience assembly."""

from __future__ import annotations

from app.services.language_writing_lesson_experience.experience_assembler import assemble_student_lesson_experience
from app.services.language_writing_lesson_experience.student_lesson_types import (
    STUDENT_LESSON_SCHEMA_VERSION,
    WritingStudentLessonExperience,
    student_lesson_fields_complete,
)

BUILDER_VERSION = "4.0.0"
FACTS_SCHEMA_VERSION = "2.0.0"
EXPERIENCE_SCHEMA_VERSION = "4.0.0"
RESPONSIBILITY = "Student Lesson Experience assembly from Mission Builder — no journey, coach, or grading fields"

# Forbidden top-level keys on WritingLessonExperienceBundle (mirror listening pattern)
LESSON_BUNDLE_FORBIDDEN_KEYS = frozenset(
    {
        "journey",
        "promotion",
        "timeline_steps",
        "unlock_checklist",
        "portfolio_index",
        "progression_scores",
        "confidence",
        "evidence",
        "readiness",
        "stability",
        "body_json",
    }
)

__all__ = [
    "BUILDER_VERSION",
    "EXPERIENCE_SCHEMA_VERSION",
    "FACTS_SCHEMA_VERSION",
    "LESSON_BUNDLE_FORBIDDEN_KEYS",
    "RESPONSIBILITY",
    "STUDENT_LESSON_SCHEMA_VERSION",
    "WritingStudentLessonExperience",
    "assemble_student_lesson_experience",
    "student_lesson_fields_complete",
]
