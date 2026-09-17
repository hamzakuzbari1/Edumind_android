"""Types for Writing AI Coach (W0/W2)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_writing.enums import WritingCoachPersonality
from app.services.language_writing_coach.memory_design import CoachMemorySnapshot
from app.services.language_writing_evaluator.types import WritingEvaluationResult
from app.services.language_writing_curriculum.types import WritingGoalProfile


@dataclass(frozen=True, slots=True)
class WritingRevisionPlan:
    """Canonical coach output for one revision turn (W2).

    Required student-facing fields per W2 architecture:
    - encouragement
    - main_issue (one main weakness)
    - priority_fix (one priority)
    - concrete_example (one example)
    - revision_mission
    - ready_to_complete
    - next_lesson_recommendation
    """

    encouragement: str
    main_issue: str
    priority_fix: str
    concrete_example: str
    revision_mission: str
    ready_to_complete: bool
    next_lesson_recommendation: str
    what_improved: tuple[str, ...] = ()
    why_it_matters: str = ""
    before_example: str = ""
    after_example: str = ""
    priority_key: str = ""
    guidance_source: str = "canonical_fallback"
    personality: WritingCoachPersonality = WritingCoachPersonality.friendly_teacher
    revision_turn: int = 1
    coach_version: str = "2.0.0"

    def to_student_dict(self) -> dict[str, object]:
        return {
            "encouragement": self.encouragement,
            "main_issue": self.main_issue,
            "main_weakness": self.main_issue,
            "priority_fix": self.priority_fix,
            "concrete_example": self.concrete_example,
            "revision_mission": self.revision_mission,
            "why_it_matters": self.why_it_matters,
            "before_example": self.before_example,
            "after_example": self.after_example,
            "priority_key": self.priority_key,
            "guidance_source": self.guidance_source,
            "ready_to_complete": self.ready_to_complete,
            "next_lesson_recommendation": self.next_lesson_recommendation,
            "next_focus": self.next_lesson_recommendation,
            "what_improved": list(self.what_improved),
        }

    def to_revision_plan_out_dict(self) -> dict[str, object]:
        """API payload for WritingRevisionPlanOut — no legacy alias fields."""
        return {
            "encouragement": self.encouragement,
            "main_issue": self.main_issue,
            "priority_fix": self.priority_fix,
            "concrete_example": self.concrete_example,
            "revision_mission": self.revision_mission,
            "why_it_matters": self.why_it_matters,
            "before_example": self.before_example,
            "after_example": self.after_example,
            "priority_key": self.priority_key,
            "guidance_source": self.guidance_source,
            "ready_to_complete": self.ready_to_complete,
            "next_lesson_recommendation": self.next_lesson_recommendation,
            "what_improved": list(self.what_improved),
        }


@dataclass(frozen=True, slots=True)
class WritingFeedback:
    """Student-facing coach output — concise teacher voice, never score-only.

    W2 note: prefer WritingRevisionPlan as canonical; this type remains for W0 API compat.
    """

    what_improved: tuple[str, ...]
    main_weakness: str
    priority_fix: str
    concrete_example: str
    encouragement: str
    next_focus: str
    ready_to_complete: bool
    personality: WritingCoachPersonality = WritingCoachPersonality.friendly_teacher

    def to_student_dict(self) -> dict[str, object]:
        return {
            "what_improved": list(self.what_improved),
            "main_weakness": self.main_weakness,
            "priority_fix": self.priority_fix,
            "concrete_example": self.concrete_example,
            "encouragement": self.encouragement,
            "next_focus": self.next_focus,
            "ready_to_complete": self.ready_to_complete,
        }


@dataclass(frozen=True, slots=True)
class CoachNarrativeContext:
    """Pre-built learning narrative for coach rendering (W7).

    Produced by the evaluation runtime from explainability output; coach never imports explainability.
    """

    coach_summary: str
    focus_sentence: str
    improvement_context: str
    strengths_summary: str
    priority_area: str


@dataclass(frozen=True, slots=True)
class CoachInputBundle:
    """Inputs for coach narrative rendering — coach must NOT re-run evaluator.

    Strict separation: evaluation facts arrive pre-computed; coach teaches only.
    """

    evaluation: WritingEvaluationResult
    goal_profile: WritingGoalProfile
    memory: CoachMemorySnapshot | None = None
    narrative_coach_summary: str = ""
    learning_outcomes: tuple[str, ...] = ()
    node_common_mistakes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CoachTrendSnapshot:
    """Coach-produced trend payload before facts assembly (coach package output)."""

    trend_headline: str
    improvement_areas: tuple[str, ...]
    sustained_skills: tuple[str, ...]
    regression_warnings: tuple[str, ...]
    comparison_window_lessons: int
    comparison_window_days: int


@dataclass(frozen=True, slots=True)
class CoachPersonalityProfile:
    """Tone wrapper — same pedagogical content, different voice."""

    personality: WritingCoachPersonality
    label: str
    tone_directives: tuple[str, ...]
    encouragement_style: str


@dataclass(frozen=True, slots=True)
class CoachInternalSignals:
    """Internal rubric signals — never exposed to student frontend."""

    task_achievement: float = 0.0
    coherence: float = 0.0
    grammar: float = 0.0
    lexis: float = 0.0
    register: float = 0.0
    organization: float = 0.0
    improvement_delta: float = 0.0
    flags: tuple[str, ...] = ()
