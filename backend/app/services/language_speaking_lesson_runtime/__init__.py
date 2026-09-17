"""Speaking Lesson Runtime (E2).

RESPONSIBILITY: Student play of frozen Learning Packages — section cursor, resume
memory, and readiness-for-discussion gate. Never regenerates packages, never calls
Claude/GPT, never evaluates, never mutates E1 frozen package content.
"""

from app.services.language_speaking_lesson_runtime.engine import (
    LESSON_RUNTIME_VERSION,
    advance_lesson_section,
    get_lesson_runtime_view,
    mark_mini_prep_complete,
    mark_teaching_block_viewed,
    mark_vocabulary_viewed,
    open_lesson_runtime,
)
from app.services.language_speaking_lesson_runtime.types import (
    LessonRuntimeSection,
    LessonRuntimeState,
)

__all__ = [
    "LESSON_RUNTIME_VERSION",
    "LessonRuntimeSection",
    "LessonRuntimeState",
    "advance_lesson_section",
    "get_lesson_runtime_view",
    "mark_mini_prep_complete",
    "mark_teaching_block_viewed",
    "mark_vocabulary_viewed",
    "open_lesson_runtime",
]
