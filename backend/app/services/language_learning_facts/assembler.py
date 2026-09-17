"""Assemble structured facts from stored lesson metadata (Phase 2.1)."""

from __future__ import annotations

from app.services.language_learning_facts.labels import slug_label
from app.services.language_learning_facts.types import (
    ChallengeFacts,
    CurriculumFacts,
    GoalFacts,
    LessonFactsBundle,
    LevelContextFacts,
    ProgressionFacts,
    PromotionContextFacts,
    SituationFacts,
)
from app.services.language_learning_goal import GOAL_KEY
from app.services.language_learning_goal.profiles import profile_for_goal
from app.services.language_learning_goal.types import LearningGoal
from app.services.language_listening_challenge.constants import LESSON_CHALLENGE_KEY
from app.services.language_listening_explainability.types import ExplainabilitySignals
from app.services.language_listening_intelligence import HISTORY_KEY
from app.services.language_listening_curriculum.memory import CURRICULUM_KEY


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _level_rank(level: str) -> int:
    order = ("A1", "A2", "B1", "B2", "C1", "C2")
    norm = str(level or "").upper()
    return order.index(norm) if norm in order else -1


def _mismatch_reason_code(
    *,
    official: str | None,
    lesson: str,
    lesson_intent: str,
    challenge_level: str,
) -> str | None:
    if not official or not lesson or official.upper() == lesson.upper():
        return None
    if lesson_intent == "review":
        return "SPECIAL_REVIEW"
    if challenge_level not in ("normal", ""):
        return "CHALLENGE_MODE"
    if _level_rank(lesson) > _level_rank(official):
        return "CHALLENGE_MODE"
    return "SPECIAL_REVIEW"


def assemble_curriculum_facts(signals: ExplainabilitySignals) -> CurriculumFacts:
    cur = signals.curriculum
    breakdown_raw = cur.get("score_breakdown") if isinstance(cur.get("score_breakdown"), dict) else {}
    breakdown: dict[str, float] = {}
    for key, raw in breakdown_raw.items():
        try:
            breakdown[str(key)] = float(raw)
        except (TypeError, ValueError):
            continue
    return CurriculumFacts(
        lesson_intent=str(cur.get("lesson_intent") or "balanced_coverage"),
        curriculum_stage=str(cur.get("curriculum_stage") or ""),
        skill_focus=tuple(str(s) for s in (cur.get("skill_focus") or []) if s),
        objectives=tuple(str(o) for o in (cur.get("objectives") or []) if o),
        review_objectives=tuple(str(o) for o in (cur.get("review_objectives") or []) if o),
        knowledge_node=str(cur.get("knowledge_node") or ""),
        recommendation_score=float(cur.get("recommendation_score") or 0.0),
        score_breakdown=breakdown,
    )


def assemble_goal_facts(signals: ExplainabilitySignals) -> GoalFacts:
    goal = signals.goal
    conf = signals.confidence_lesson
    raw_goal = str(goal.get("learning_goal") or conf.get("learning_goal") or "").strip()
    goal_id: str | None = None
    profile_label: str | None = str(goal.get("goal_profile") or "").strip() or None
    if raw_goal:
        try:
            parsed = LearningGoal(raw_goal)
            goal_id = parsed.value
            if not profile_label:
                profile_label = profile_for_goal(parsed).label
        except ValueError:
            goal_id = raw_goal
            profile_label = profile_label or slug_label(raw_goal)
    hints = tuple(str(h) for h in (goal.get("goal_objective_hints") or []) if h)
    return GoalFacts(
        lesson_goal_id=goal_id,
        goal_profile_label=profile_label,
        goal_alignment_score=float(goal.get("goal_alignment_score") or 0.0),
        goal_objective_hints=hints,
        selection_reason_code=str(goal.get("goal_selection_reason") or goal.get("selection_reason") or ""),
    )


def assemble_challenge_facts(signals: ExplainabilitySignals) -> ChallengeFacts:
    intel = signals.intelligence
    ch = signals.challenge_lesson
    intel_band = str(intel.get("difficulty_band") or "normal")
    challenge_level = str(ch.get("challenge_level") or "normal")
    return ChallengeFacts(
        challenge_level=challenge_level,
        challenge_label=str(ch.get("challenge_label") or f"{signals.cefr_level} {challenge_level.title()}"),
        challenge_score=float(ch.get("challenge_score") or 0.0),
        effective_difficulty_band=str(ch.get("effective_difficulty_band") or intel_band),
        promote_streak=int(ch.get("promote_streak") or 0),
        demote_streak=int(ch.get("demote_streak") or 0),
        promotion_count=int(ch.get("promotion_count") or 0),
        challenge_reason_code=f"challenge_{challenge_level}",
        selection_reason_code=str(ch.get("challenge_selection_reason") or ch.get("selection_reason") or ""),
    )


def assemble_situation_facts(signals: ExplainabilitySignals) -> SituationFacts:
    intel = signals.intelligence
    return SituationFacts(
        situation_id=str(intel.get("situation") or ""),
        category=str(intel.get("category") or ""),
        narrative_format=str(intel.get("narrative_format") or intel.get("format_hint") or ""),
        pace=str(intel.get("pace") or ""),
        intelligence_difficulty_band=str(intel.get("difficulty_band") or "normal"),
    )


def assemble_level_context_facts(
    signals: ExplainabilitySignals,
    *,
    official_level: str | None = None,
    journey_target_level: str | None = None,
    lesson_level: str | None = None,
) -> LevelContextFacts:
    lesson = lesson_level or signals.cefr_level
    official = str(official_level or "").upper() or None
    mismatch = bool(official and lesson and official != lesson.upper())
    cur = signals.curriculum
    ch = signals.challenge_lesson
    return LevelContextFacts(
        cefr_level=signals.cefr_level,
        lesson_level=lesson,
        official_level=official,
        journey_target_level=journey_target_level,
        mismatch=mismatch,
        mismatch_reason_code=_mismatch_reason_code(
            official=official,
            lesson=lesson,
            lesson_intent=str(cur.get("lesson_intent") or ""),
            challenge_level=str(ch.get("challenge_level") or "normal"),
        )
        if mismatch
        else None,
    )


def assemble_progression_facts(
    *,
    official_level: str | None = None,
    journey_target_level: str | None = None,
    readiness_band: str | None = None,
    estimated_lessons_remaining: int | None = None,
    can_start_promotion_test: bool = False,
    readiness_score: float | None = None,
) -> ProgressionFacts:
    promotion: PromotionContextFacts | None = None
    if any(
        v is not None
        for v in (readiness_band, estimated_lessons_remaining, readiness_score)
    ) or can_start_promotion_test:
        promotion = PromotionContextFacts(
            readiness_band=readiness_band,
            estimated_lessons_remaining=estimated_lessons_remaining,
            can_start_promotion_test=can_start_promotion_test,
            readiness_score=readiness_score,
        )
    return ProgressionFacts(
        official_level=str(official_level or "").upper() or None,
        journey_target_level=str(journey_target_level or "").upper() or None,
        promotion=promotion,
    )


def assemble_lesson_facts(
    body_json: dict | None,
    *,
    lesson_id: int | None = None,
    lesson_title: str | None = None,
    lesson_type: str = "practice",
    cefr_level: str = "",
    official_level: str | None = None,
    journey_target_level: str | None = None,
    lesson_level: str | None = None,
    weak_skills: list[str] | None = None,
) -> LessonFactsBundle:
    """Build lesson-scoped facts from stored body_json metadata."""
    from app.services.language_listening_explainability.signals import extract_signals

    signals = extract_signals(body_json, cefr_level=cefr_level, weak_skills=weak_skills)
    body = body_json or {}
    level = lesson_level or signals.cefr_level or str(_as_dict(body.get(HISTORY_KEY)).get("level") or "A1")
    return LessonFactsBundle(
        lesson_id=lesson_id,
        lesson_title=lesson_title,
        lesson_type=lesson_type,
        question_types=signals.question_types,
        situation=assemble_situation_facts(signals),
        curriculum=assemble_curriculum_facts(signals),
        goal=assemble_goal_facts(signals),
        challenge=assemble_challenge_facts(signals),
        level=assemble_level_context_facts(
            signals,
            official_level=official_level,
            journey_target_level=journey_target_level,
            lesson_level=level,
        ),
    )


def top_curriculum_factors(curriculum: CurriculumFacts, *, limit: int = 2) -> tuple[tuple[str, float], ...]:
    from app.services.language_listening_explainability.signals import top_score_factors

    return tuple(top_score_factors(curriculum.score_breakdown, limit=limit))
