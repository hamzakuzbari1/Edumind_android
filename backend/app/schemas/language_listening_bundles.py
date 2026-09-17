"""Canonical Listening bundles (Phase 2.3) — closed contracts per architecture v3.0."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.language_learning import LessonProgressOut, LessonQuestionOut

# Forbidden top-level keys on LessonExperienceBundle (Section 5.6)
LESSON_BUNDLE_FORBIDDEN_KEYS = frozenset(
    {
        "journey",
        "promotion",
        "history",
        "personal_goal",
        "journey_target",
        "timeline_steps",
        "unlock_checklist",
        "history_events",
        "coach",
        "body_json",
        "transcript",
        "goal",
        "learning_goal",
        "target_goal",
    }
)

JourneyLifecycleState = Literal["queued", "reserved", "started", "completed", "reviewed"]
LessonType = Literal["practice", "review", "promotion_assessment", "placement"]


class LessonGoalOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str


class LessonNarrativeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_selected: str = ""
    why_this_lesson: str = ""
    student_focus: list[str] = Field(default_factory=list)
    expected_improvement: list[str] = Field(default_factory=list)
    challenge_reason: str = ""
    reward: str = ""
    next_after_this: str = ""
    coach_summary: str = ""


class LessonPlaybackOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instructions: str | None = None
    questions: list[LessonQuestionOut] = Field(default_factory=list)
    audio_url: str | None = None
    audio_available: bool = False
    progress: LessonProgressOut = Field(default_factory=LessonProgressOut)


class AfterLessonOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = ""
    summary: str = ""
    improved: list[str] = Field(default_factory=list)
    needs_practice: list[str] = Field(default_factory=list)
    next_lesson_teaser: str = ""
    coach_summary: str = ""


class LessonExperienceMetaOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    builder_version: str = "2.3.0"
    facts_schema_version: str = "1.0"
    reservation_id: str | None = None
    pinned_until: Literal["completed", "skipped", "expired"] | None = None
    activity_session_id: str | None = None
    grammar_id: str | None = None
    grammar_title: str | None = None


class LessonExperienceBundleOut(BaseModel):
    """Canonical lesson-scoped bundle — Section 5.1 only."""

    model_config = ConfigDict(extra="forbid")

    lesson_id: int
    lifecycle_state: JourneyLifecycleState
    official_level: str
    lesson_level: str
    level_note: str | None = None
    lesson_title: str
    lesson_type: LessonType = "practice"
    situation: str = ""
    lesson_goal: LessonGoalOut
    narrative: LessonNarrativeOut = Field(default_factory=LessonNarrativeOut)
    playback: LessonPlaybackOut = Field(default_factory=LessonPlaybackOut)
    after_lesson: AfterLessonOut | None = None
    meta: LessonExperienceMetaOut = Field(default_factory=LessonExperienceMetaOut)


class JourneyTargetOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str
    label: str


class PersonalGoalOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str


class TimelineStepOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    done: bool = False
    active: bool = False
    current: bool = False


class HistoryEventOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str
    text: str


class JourneyNarrativeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    journey_headline: str = ""
    current_step_label: str = ""
    promotion_progress_message: str = ""
    unlock_checklist: list[str] = Field(default_factory=list)
    timeline_steps: list[TimelineStepOut] = Field(default_factory=list)
    history_events: list[HistoryEventOut] = Field(default_factory=list)


class JourneyPromotionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    readiness_band: str = "NOT_READY"
    can_start_test: bool = False
    estimated_lessons_remaining: int | None = None
    primary_blockers: list[str] = Field(default_factory=list)


class ActiveLessonPointerOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lesson_id: int | None = None
    lifecycle_state: JourneyLifecycleState | None = None


class ListeningJourneyMetaOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    builder_version: str = "2.3.0"


class ListeningJourneyBundleOut(BaseModel):
    """Canonical journey-scoped bundle — Section 7.1 only."""

    model_config = ConfigDict(extra="forbid")

    official_level: str
    learning_stage: int = 1
    learning_stage_label: str = ""
    journey_target: JourneyTargetOut
    personal_goal: PersonalGoalOut
    narrative: JourneyNarrativeOut = Field(default_factory=JourneyNarrativeOut)
    promotion: JourneyPromotionOut = Field(default_factory=JourneyPromotionOut)
    active_lesson: ActiveLessonPointerOut = Field(default_factory=ActiveLessonPointerOut)
    meta: ListeningJourneyMetaOut = Field(default_factory=ListeningJourneyMetaOut)


class ListeningLessonSubmitBundleOut(BaseModel):
    """Submit response: canonical bundle + mechanical grading (not educational copy)."""

    model_config = ConfigDict(extra="forbid")

    bundle: LessonExperienceBundleOut
    passed: bool
    score_percent: float
    correct_count: int
    total_questions: int
    question_results: list[dict] = Field(default_factory=list)
