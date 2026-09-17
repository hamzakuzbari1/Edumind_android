"""Student Grammar Module contracts (Product Milestone A)."""

from __future__ import annotations

from dataclasses import dataclass

GRAMMAR_MODULE_SCHEMA_VERSION = 1
GRAMMAR_MODULE_PACKAGE_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class GrammarDashboardView:
    enabled: bool
    current_cefr: str = ""
    grammar_target: str | None = None
    difficulty: str = "guided"
    estimated_minutes: int = 10
    lesson_goal: str = ""
    has_lesson_preview: bool = False
    empty_state_message: str = ""


@dataclass(frozen=True, slots=True)
class GrammarLessonView:
    lesson_id: str
    grammar_target: str
    lesson_title: str
    teacher_opening: str
    lesson_goal: str
    warmup: str
    main_activity: str
    follow_up_questions: tuple[str, ...]
    teacher_hints: tuple[str, ...]
    common_mistakes: tuple[dict[str, str], ...]
    expected_patterns: tuple[str, ...]
    completion_message: str
    estimated_minutes: int
    difficulty: str
