"""Types for Writing Promotion Assessment (WPA) — W0."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_writing.enums import OfficialWritingCEFR, PromotionStatus, WritingGoal


@dataclass(frozen=True, slots=True)
class WritingPromotionTask:
    """Single timed writing task in a WPA session."""

    task_id: str
    task_type: str  # email, opinion, essay, report, summary, review, etc.
    genre: str
    prompt: str
    min_words: int
    max_words: int
    time_limit_minutes: int
    rubric_criteria: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WritingGoalPromotionBundle:
    """Goal-specific WPA task bundle definition."""

    goal: WritingGoal
    bundle_key: str
    label: str
    tasks: tuple[WritingPromotionTask, ...]
    min_cefr: OfficialWritingCEFR
    max_cefr: OfficialWritingCEFR


# Goal → bundle mapping (canonical v1)
GOAL_WPA_BUNDLE_KEYS: dict[WritingGoal, str] = {
    WritingGoal.ielts: "ielts_task1_task2",
    WritingGoal.business: "business_email_report",
    WritingGoal.travel: "travel_complaint_request",
    WritingGoal.academic: "academic_summary_essay",
    WritingGoal.creative_writing: "creative_narrative_description",
    WritingGoal.job_interview: "job_cover_intro",
    WritingGoal.daily_communication: "daily_message_note",
    WritingGoal.general_english: "general_mixed_practical",
}


@dataclass(frozen=True, slots=True)
class WritingPromotionBundle:
    """Active WPA session bundle for a student."""

    session_id: str
    student_id: int
    language_id: int
    official_cefr: OfficialWritingCEFR
    target_cefr: OfficialWritingCEFR
    goal: WritingGoal
    tasks: tuple[WritingPromotionTask, ...]
    status: PromotionStatus = PromotionStatus.in_progress


@dataclass(frozen=True, slots=True)
class WritingPromotionTaskResult:
    task_id: str
    submitted_text: str
    word_count: int
    criterion_scores: dict[str, float] = field(default_factory=dict)
    passed: bool = False


@dataclass(frozen=True, slots=True)
class WritingPromotionResult:
    session_id: str
    overall_passed: bool
    task_results: tuple[WritingPromotionTaskResult, ...]
    status: PromotionStatus
