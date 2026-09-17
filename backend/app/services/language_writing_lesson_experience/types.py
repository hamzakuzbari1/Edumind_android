"""Types for Writing Lesson Experience (W0)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_writing.enums import WritingLessonLifecycle
from app.services.language_writing_coach.types import WritingFeedback
from app.services.language_writing_revision.types import WritingDraft, WritingRevision


@dataclass(frozen=True, slots=True)
class WritingMission:
    """Student-facing mission card — explains WHY, not engine terms."""

    title: str
    prompt: str
    why_today: str
    learning_goal_text: str
    task_type: str
    genre: str
    min_words: int
    max_words: int
    time_limit_minutes: int | None = None
    checklist: tuple[str, ...] = ()
    scaffold_outline: tuple[str, ...] = ()
    carry_forward: str = ""


@dataclass(frozen=True, slots=True)
class WritingComposerState:
    """Editor/composer section of lesson experience."""

    draft_text: str = ""
    word_count: int = 0
    can_submit: bool = True
    lifecycle: WritingLessonLifecycle = WritingLessonLifecycle.drafting


@dataclass(frozen=True, slots=True)
class WritingLessonExperienceBundle:
    """Canonical lesson-scoped bundle — mission + composer + coach + revision timeline."""

    lesson_id: int
    lifecycle_state: WritingLessonLifecycle
    official_level: str
    lesson_level: str
    lesson_title: str
    mission: WritingMission
    composer: WritingComposerState = field(default_factory=WritingComposerState)
    coach: WritingFeedback | None = None
    revision_timeline: tuple[WritingRevision, ...] = ()
    draft_history: tuple[WritingDraft, ...] = ()
    builder_version: str = "0.1.0"
    facts_schema_version: str = "1.0.0"
    reservation_id: str | None = None

    def forbidden_keys_present(self) -> frozenset[str]:
        from app.services.language_writing_lesson_experience import LESSON_BUNDLE_FORBIDDEN_KEYS

        present: set[str] = set()
        for key in LESSON_BUNDLE_FORBIDDEN_KEYS:
            if hasattr(self, key):
                present.add(key)
        return frozenset(present)
