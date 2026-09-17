"""Learning Narrative Builder (Phase 2.1) — sole owner of student-facing educational copy."""

from app.services.language_learning_narrative.builder import (
    build_after_lesson_narrative,
    build_lesson_narrative,
)
from app.services.language_learning_narrative.legacy_adapter import (
    legacy_lesson_explainability,
    legacy_student_summary,
)
from app.services.language_learning_narrative.types import AfterLessonNarrative, LessonNarrative

__all__ = (
    "AfterLessonNarrative",
    "LessonNarrative",
    "build_after_lesson_narrative",
    "build_lesson_narrative",
    "legacy_lesson_explainability",
    "legacy_student_summary",
)
