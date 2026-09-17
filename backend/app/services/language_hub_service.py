"""Hub and progress dashboard payloads."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.analytics import LanguageAnalytics
from app.models.language.assessment import LanguageAssessment
from app.models.language.enums import LanguageContentProgressStatus
from app.models.language.engagement import LanguageActivityLog
from app.models.language.path import LanguageLearningPath, LanguagePathItem
from app.models.language.profile import LanguageStudentProfile
from app.services.language_analytics_service import build_skill_growth_snapshot, get_streak, refresh_language_analytics
from app.services.language_level_utils import bottleneck_level
from app.services.language_subscription_service import get_default_language


def _levels_dict(analytics: LanguageAnalytics | None) -> dict[str, str | None]:
    if not analytics:
        return {"reading": None, "listening": None, "writing": None, "speaking": None, "overall": None}
    levels = {
        "reading": analytics.reading_level.value if analytics.reading_level else None,
        "listening": analytics.listening_level.value if analytics.listening_level else None,
        "writing": analytics.writing_level.value if analytics.writing_level else None,
        "speaking": analytics.speaking_level.value if analytics.speaking_level else None,
    }
    overall = bottleneck_level(levels)
    levels["overall"] = overall.value if overall else None
    return levels


async def build_language_hub(db: AsyncSession, *, student_id: int) -> dict:
    language = await get_default_language(db)
    analytics = await refresh_language_analytics(db, student_id=student_id, language_id=language.id)
    growth = analytics.skill_growth_json or await build_skill_growth_snapshot(
        db, student_id=student_id, language_id=language.id, analytics=analytics
    )

    profile = await db.execute(
        select(LanguageStudentProfile).where(
            LanguageStudentProfile.student_id == student_id,
            LanguageStudentProfile.language_id == language.id,
        )
    )
    prof = profile.scalar_one_or_none()

    assessment_row = await db.execute(
        select(LanguageAssessment)
        .where(LanguageAssessment.student_id == student_id, LanguageAssessment.language_id == language.id)
        .order_by(LanguageAssessment.completed_at.desc())
        .limit(1)
    )
    latest_assessment = assessment_row.scalar_one_or_none()

    can_retake = True
    next_retake = prof.next_allowed_retake_date if prof else None
    if next_retake is not None:
        now = datetime.now(timezone.utc)
        retake_dt = next_retake if next_retake.tzinfo else next_retake.replace(tzinfo=timezone.utc)
        can_retake = retake_dt <= now

    path_row = await db.execute(
        select(LanguageLearningPath)
        .where(LanguageLearningPath.student_id == student_id, LanguageLearningPath.language_id == language.id)
        .order_by(LanguageLearningPath.generated_at.desc())
        .limit(1)
    )
    path = path_row.scalar_one_or_none()
    items_total = 0
    items_completed = 0
    if path:
        counts = await db.execute(
            select(
                func.count(LanguagePathItem.id),
                func.coalesce(
                    func.sum(
                        case(
                            (LanguagePathItem.status == LanguageContentProgressStatus.completed, 1),
                            else_=0,
                        )
                    ),
                    0,
                ),
            ).where(LanguagePathItem.path_id == path.id)
        )
        row = counts.one()
        items_total = int(row[0] or 0)
        items_completed = int(row[1] or 0)

    return {
        "levels": _levels_dict(analytics),
        "skill_growth": {
            "reading": growth.get("reading"),
            "listening": growth.get("listening"),
            "writing": growth.get("writing"),
            "speaking": growth.get("speaking"),
            "vocabulary": growth.get("vocabulary"),
        },
        "target_level": prof.target_level.value if prof and prof.target_level else None,
        "target_date": prof.target_date if prof else None,
        "placement": {
            "completed_at": prof.placement_completed_at if prof else None,
            "overall_level": latest_assessment.overall_level.value if latest_assessment and latest_assessment.overall_level else None,
            "can_retake": can_retake,
            "next_allowed_retake_date": next_retake,
        },
        "learning_path": {
            "path_id": path.id if path else None,
            "generated_at": path.generated_at if path else None,
            "items_total": items_total,
            "items_completed": items_completed,
        },
        "quick_stats": {
            "reading_completion_percent": growth.get("reading_completion_percent", 0),
            "listening_completion_percent": growth.get("listening_completion_percent", 0),
            "completed_activities": growth.get("completed_activities", 0),
        },
    }


async def build_language_progress(db: AsyncSession, *, student_id: int) -> dict:
    language = await get_default_language(db)
    analytics = await refresh_language_analytics(db, student_id=student_id, language_id=language.id)
    growth = analytics.skill_growth_json or {}

    profile = await db.execute(
        select(LanguageStudentProfile).where(
            LanguageStudentProfile.student_id == student_id,
            LanguageStudentProfile.language_id == language.id,
        )
    )
    prof = profile.scalar_one_or_none()
    streak = await get_streak(db, student_id=student_id, language_id=language.id)

    activity_rows = await db.execute(
        select(LanguageActivityLog)
        .where(LanguageActivityLog.student_id == student_id, LanguageActivityLog.language_id == language.id)
        .order_by(LanguageActivityLog.created_at.desc())
        .limit(10)
    )
    recent = []
    for log in activity_rows.scalars().all():
        payload = log.payload_json or {}
        recent.append(
            {
                "id": log.id,
                "event_type": log.event_type,
                "skill": log.skill.value if log.skill else None,
                "title": payload.get("title"),
                "score_percent": payload.get("score_percent"),
                "created_at": log.created_at,
            }
        )

    levels = _levels_dict(analytics)
    return {
        "overall_level": levels.get("overall"),
        "reading_level": levels.get("reading"),
        "listening_level": levels.get("listening"),
        "writing_level": levels.get("writing"),
        "speaking_level": levels.get("speaking"),
        "skill_growth": {
            "reading": growth.get("reading"),
            "listening": growth.get("listening"),
            "writing": growth.get("writing"),
            "speaking": growth.get("speaking"),
            "vocabulary": growth.get("vocabulary"),
        },
        "completed_activities": int(growth.get("completed_activities") or 0),
        "reading_completion_percent": int(growth.get("reading_completion_percent") or 0),
        "listening_completion_percent": int(growth.get("listening_completion_percent") or 0),
        "writing_completion_percent": int(growth.get("writing_completion_percent") or 0),
        "speaking_completion_percent": int(growth.get("speaking_completion_percent") or 0),
        "vocabulary_count": int(analytics.vocabulary_count or 0),
        "vocabulary_learned": int(growth.get("vocabulary_learned") or 0),
        "vocabulary_learning": int(growth.get("vocabulary_learning") or 0),
        "writing_completed": int(growth.get("writing_completed") or 0),
        "speaking_completed": int(growth.get("speaking_completed") or 0),
        "current_streak": int(streak.current_streak if streak else 0),
        "longest_streak": int(streak.longest_streak if streak else 0),
        "recent_activity": recent,
        "target_level": prof.target_level.value if prof and prof.target_level else None,
        "target_date": prof.target_date if prof else None,
    }
