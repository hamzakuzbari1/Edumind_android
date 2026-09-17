"""Structured fact types for the Facts Layer (Phase 2.1)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ObjectiveConfidenceFact:
    objective_id: str
    confidence: float
    coverage: float
    mastery: float


@dataclass(frozen=True, slots=True)
class SelectionRationaleFacts:
    primary_engine: str
    lesson_intent: str
    curriculum_stage: str
    recommendation_score: float
    top_score_factors: tuple[tuple[str, float], ...] = ()
    selection_reason_code: str = ""
    goal_id: str | None = None
    goal_alignment_score: float = 0.0


@dataclass(frozen=True, slots=True)
class SituationFacts:
    situation_id: str
    category: str
    narrative_format: str
    pace: str
    intelligence_difficulty_band: str


@dataclass(frozen=True, slots=True)
class LevelContextFacts:
    cefr_level: str
    lesson_level: str
    official_level: str | None
    journey_target_level: str | None
    mismatch: bool
    mismatch_reason_code: str | None


@dataclass(frozen=True, slots=True)
class ChallengeFacts:
    challenge_level: str
    challenge_label: str
    challenge_score: float
    effective_difficulty_band: str
    promote_streak: int
    demote_streak: int
    promotion_count: int
    challenge_reason_code: str
    selection_reason_code: str = ""


@dataclass(frozen=True, slots=True)
class CurriculumFacts:
    lesson_intent: str
    curriculum_stage: str
    skill_focus: tuple[str, ...]
    objectives: tuple[str, ...]
    review_objectives: tuple[str, ...]
    knowledge_node: str
    recommendation_score: float
    score_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GoalFacts:
    lesson_goal_id: str | None
    goal_profile_label: str | None
    goal_alignment_score: float
    goal_objective_hints: tuple[str, ...] = ()
    selection_reason_code: str = ""


@dataclass(frozen=True, slots=True)
class PromotionContextFacts:
    readiness_band: str | None
    estimated_lessons_remaining: int | None
    can_start_promotion_test: bool
    readiness_score: float | None


@dataclass(frozen=True, slots=True)
class ProgressionFacts:
    official_level: str | None
    journey_target_level: str | None
    promotion: PromotionContextFacts | None = None


@dataclass(frozen=True, slots=True)
class PostLessonFacts:
    score_percent: float
    passed: bool
    correct_count: int
    total_questions: int
    objectives_correct: tuple[str, ...] = ()
    objectives_incorrect: tuple[str, ...] = ()
    readiness_delta: float | None = None


@dataclass(frozen=True, slots=True)
class PersonalGoalFacts:
    personal_goal_id: str
    personal_goal_label: str


@dataclass(frozen=True, slots=True)
class JourneyTargetFacts:
    level: str
    label: str


@dataclass(frozen=True, slots=True)
class JourneyPromotionFacts:
    readiness_band: str
    readiness_score: int
    can_start_test: bool
    estimated_lessons_remaining: int | None
    primary_blockers: tuple[str, ...] = ()
    secondary_blockers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class JourneyHistoryFacts:
    last_attempt_result: str | None = None
    last_attempt_target_cefr: str | None = None
    last_attempt_official_cefr: str | None = None
    latest_recommendation: str | None = None
    stability_prediction: str | None = None
    has_active_test_session: bool = False
    promoted: bool = False


@dataclass(frozen=True, slots=True)
class ActiveLessonFacts:
    lesson_id: int | None
    lifecycle_state: str | None


@dataclass(frozen=True, slots=True)
class JourneyFactsBundle:
    """Journey-scoped facts assembled for Journey Builder (Phase 2.3)."""

    official_level: str
    journey_target: JourneyTargetFacts
    personal_goal: PersonalGoalFacts
    promotion: JourneyPromotionFacts
    history: JourneyHistoryFacts
    active_lesson: ActiveLessonFacts


@dataclass(frozen=True, slots=True)
class LessonFactsBundle:
    """Aggregated lesson-scoped facts assembled from stored metadata."""

    lesson_id: int | None
    lesson_title: str | None
    lesson_type: str
    question_types: tuple[str, ...]
    situation: SituationFacts
    curriculum: CurriculumFacts
    goal: GoalFacts
    challenge: ChallengeFacts
    level: LevelContextFacts


def facts_to_dict(obj: object) -> object:
    """Serialize fact dataclasses for verification and logging."""
    if hasattr(obj, "__dataclass_fields__"):
        out: dict[str, object] = {}
        for key in obj.__dataclass_fields__:
            val = getattr(obj, key)
            out[key] = facts_to_dict(val)
        return out
    if isinstance(obj, tuple):
        return [facts_to_dict(v) for v in obj]
    if isinstance(obj, dict):
        return {k: facts_to_dict(v) for k, v in obj.items()}
    return obj
