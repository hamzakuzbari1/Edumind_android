"""Full language analytics dashboard payload (Phase 7.8)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_achievement_service import count_earned_achievements, list_student_achievements
from app.services.language_analytics_service import get_streak, refresh_language_analytics
from app.services.language_daily_plan_service import build_daily_plan
from app.services.language_level_utils import SKILL_LABELS_AR, bottleneck_level
from app.services.language_statistics_service import (
    compute_improvement_trend,
    list_scenario_progress,
    refresh_statistics_on_analytics,
)
from app.services.language_subscription_service import get_default_language


def _skill_scores(growth: dict) -> dict[str, int | None]:
    def _score(skill: str) -> int | None:
        g = growth.get(skill) or {}
        if skill == "vocabulary":
            return int(g.get("growth_percent") or 0)
        avg = g.get("average_score_percent")
        if avg is not None:
            return int(round(float(avg)))
        return int(g.get("growth_percent") or 0)

    return {
        "reading": _score("reading"),
        "listening": _score("listening"),
        "writing": _score("writing"),
        "speaking": _score("speaking"),
        "vocabulary": _score("vocabulary"),
    }


def _overall_progress_percent(growth: dict, curriculum_mastery: int) -> int:
    parts = []
    for sk in ("reading", "listening", "writing", "speaking"):
        g = growth.get(sk) or {}
        parts.append(int(g.get("growth_percent") or 0))
    vocab = int((growth.get("vocabulary") or {}).get("growth_percent") or 0)
    parts.append(vocab)
    skill_avg = int(round(sum(parts) / len(parts))) if parts else 0
    if curriculum_mastery:
        return int(round(0.6 * skill_avg + 0.4 * curriculum_mastery))
    return skill_avg


def _strongest_weakest(skill_scores: dict[str, int | None]) -> tuple[str | None, str | None, str | None, str | None]:
    scored = {
        skill: score
        for skill, score in skill_scores.items()
        if skill != "vocabulary" and score is not None
    }
    strongest = max(scored, key=scored.get) if scored else None
    weakest = min(scored, key=scored.get) if scored else None
    return (
        strongest,
        SKILL_LABELS_AR.get(strongest or "", strongest),
        weakest,
        SKILL_LABELS_AR.get(weakest or "", weakest),
    )


async def build_language_analytics_dashboard(db: AsyncSession, *, student_id: int) -> dict:
    language = await get_default_language(db)
    lang_id = language.id

    analytics = await refresh_language_analytics(db, student_id=student_id, language_id=lang_id)
    growth = analytics.skill_growth_json or {}
    skill_scores = _skill_scores(growth)
    stats = await refresh_statistics_on_analytics(db, student_id=student_id, language_id=lang_id)
    trend = await compute_improvement_trend(db, student_id=student_id, language_id=lang_id)
    achievements = await list_student_achievements(db, student_id=student_id, language_id=lang_id)
    scenarios = await list_scenario_progress(db, student_id=student_id, language_id=lang_id)
    daily = await build_daily_plan(db, student_id=student_id)
    streak = await get_streak(db, student_id=student_id, language_id=lang_id)

    levels = {
        "reading": analytics.reading_level.value if analytics.reading_level else None,
        "listening": analytics.listening_level.value if analytics.listening_level else None,
        "writing": analytics.writing_level.value if analytics.writing_level else None,
        "speaking": analytics.speaking_level.value if analytics.speaking_level else None,
    }
    overall = bottleneck_level(levels)
    strongest, strongest_ar, weakest, weakest_ar = _strongest_weakest(skill_scores)

    obj_total = int(daily.get("objectives_total") or 0)
    obj_mastered = int(daily.get("objectives_mastered") or 0)
    curriculum_mastery = int(round(100 * obj_mastered / obj_total)) if obj_total else 0

    daily_items = daily.get("items") or []
    daily_done = sum(1 for i in daily_items if i.get("done"))
    daily_total = len(daily_items)

    earned_badges = [a for a in achievements["achievements"] if a["earned"]][-6:]

    return {
        "current_cefr_level": overall.value if overall else None,
        "adaptive_recommendation": None,
        "adaptive_recommendation_ar": daily.get("adaptive_detail_ar"),
        "overall_progress_percent": _overall_progress_percent(growth, curriculum_mastery),
        "skill_scores": skill_scores,
        "levels": {**levels, "overall": overall.value if overall else None},
        "strongest_skill": strongest,
        "strongest_skill_ar": strongest_ar,
        "weakest_skill": weakest,
        "weakest_skill_ar": weakest_ar,
        "improvement_trend": trend,
        "statistics": stats,
        "achievements": achievements,
        "recent_badges": earned_badges,
        "scenario_progress": scenarios,
        "skill_radar": [
            {"skill": sk, "label_ar": SKILL_LABELS_AR.get(sk, sk), "score": skill_scores.get(sk) or 0}
            for sk in ("reading", "listening", "writing", "speaking", "vocabulary")
        ],
        "daily_mission": {
            "completed": daily_done,
            "total": daily_total,
            "percent": int(round(100 * daily_done / daily_total)) if daily_total else 0,
            "recommendation": None,
            "detail_ar": daily.get("adaptive_detail_ar"),
        },
        "streak": {
            "current": int(streak.current_streak if streak else 0),
            "longest": int(streak.longest_streak if streak else 0),
        },
        "skill_growth": growth,
    }


async def build_parent_language_analytics_summary(db: AsyncSession, *, student_id: int) -> dict | None:
    """Read-only language summary for parent dashboards."""
    language = await get_default_language(db)
    lang_id = language.id
    dashboard = await build_language_analytics_dashboard(db, student_id=student_id)
    earned = await count_earned_achievements(db, student_id=student_id, language_id=lang_id)
    scenarios_done = dashboard["statistics"].get("scenarios_completed", 0)
    return {
        "current_cefr_level": dashboard["current_cefr_level"],
        "strongest_skill": dashboard["strongest_skill"],
        "strongest_skill_ar": dashboard["strongest_skill_ar"],
        "weakest_skill": dashboard["weakest_skill"],
        "weakest_skill_ar": dashboard["weakest_skill_ar"],
        "completed_scenarios": scenarios_done,
        "achievements_count": earned,
        "overall_progress_percent": dashboard["overall_progress_percent"],
        "adaptive_recommendation": dashboard["adaptive_recommendation"],
    }
