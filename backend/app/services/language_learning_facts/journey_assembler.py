"""Assemble journey-scoped facts (Phase 2.3)."""

from __future__ import annotations

from app.services.language_learning_facts.types import (
    ActiveLessonFacts,
    JourneyFactsBundle,
    JourneyHistoryFacts,
    JourneyPromotionFacts,
    JourneyTargetFacts,
    PersonalGoalFacts,
)
from app.services.language_learning_goal.profiles import profile_for_goal
from app.services.language_learning_goal.resolver import resolve_learning_goal
from app.services.language_learning_goal.types import LearningGoal
from app.services.language_promotion_readiness.types import PromotionReadinessResult, ReadinessStatus
from app.services.language_promotion_stability.types import PromotionStabilityResult


def _next_cefr(level: str) -> str:
    order = ("A1", "A2", "B1", "B2", "C1", "C2")
    norm = str(level or "").upper()
    if norm not in order:
        return "A2"
    idx = order.index(norm)
    return order[min(idx + 1, len(order) - 1)]


def _journey_target_label(level: str) -> str:
    return f"Unlock {level}"


def assemble_journey_facts(
    *,
    official_level: str,
    personal_goal: LearningGoal,
    readiness: PromotionReadinessResult,
    stability: PromotionStabilityResult | None = None,
    eligibility_can_start: bool = False,
    target_cefr: str | None = None,
    active_lesson_id: int | None = None,
    active_lifecycle: str | None = None,
    last_attempt_result: str | None = None,
    last_attempt_target_cefr: str | None = None,
    last_attempt_official_cefr: str | None = None,
    latest_recommendation: str | None = None,
    has_active_test_session: bool = False,
    promoted: bool = False,
) -> JourneyFactsBundle:
    official = str(official_level or "A1").upper()
    target = str(target_cefr or _next_cefr(official)).upper()
    goal_profile = profile_for_goal(personal_goal)
    can_start = bool(
        eligibility_can_start and readiness.status == ReadinessStatus.PROMOTION_AVAILABLE
    )
    return JourneyFactsBundle(
        official_level=official,
        journey_target=JourneyTargetFacts(level=target, label=_journey_target_label(target)),
        personal_goal=PersonalGoalFacts(
            personal_goal_id=personal_goal.value,
            personal_goal_label=goal_profile.label,
        ),
        promotion=JourneyPromotionFacts(
            readiness_band=readiness.status.value,
            readiness_score=int(readiness.readiness_score),
            can_start_test=can_start,
            estimated_lessons_remaining=readiness.estimated_remaining,
            primary_blockers=tuple(readiness.primary_blockers),
            secondary_blockers=tuple(readiness.secondary_blockers),
        ),
        history=JourneyHistoryFacts(
            last_attempt_result=last_attempt_result,
            last_attempt_target_cefr=last_attempt_target_cefr,
            last_attempt_official_cefr=last_attempt_official_cefr,
            latest_recommendation=latest_recommendation,
            stability_prediction=stability.prediction.value if stability else None,
            has_active_test_session=has_active_test_session,
            promoted=promoted,
        ),
        active_lesson=ActiveLessonFacts(
            lesson_id=active_lesson_id,
            lifecycle_state=active_lifecycle,
        ),
    )


def resolve_personal_goal_from_memory(
    *,
    learning_goals: list[str] | None = None,
    future_goal: str | None = None,
) -> LearningGoal:
    return resolve_learning_goal(future_goal=future_goal, learning_goals=learning_goals)
