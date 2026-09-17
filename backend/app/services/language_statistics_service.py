"""Aggregate language learning statistics for analytics dashboards."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.analytics import LanguageAnalytics
from app.models.language.conversation import LanguageSpeakingConversationSession
from app.models.language.engagement import LanguageActivityLog
from app.models.language.progress import LanguageSpeakingProgress, LanguageWritingProgress
from app.models.language.scenario_progress import LanguageScenarioProgress
from app.services.language_curriculum_service import build_curriculum_overview


def _avg_score_from_payload(payload: dict | None) -> float | None:
    if not payload:
        return None
    if payload.get("score_percent") is not None:
        try:
            return float(payload["score_percent"])
        except (TypeError, ValueError):
            pass
    scores = payload.get("scores")
    if isinstance(scores, dict) and scores:
        vals = []
        for v in scores.values():
            try:
                vals.append(float(v))
            except (TypeError, ValueError):
                continue
        if vals:
            return sum(vals) / len(vals)
    return None


async def compute_language_statistics(
    db: AsyncSession, *, student_id: int, language_id: int
) -> dict:
    """Roll up counters from activity log, progress tables, and curriculum."""
    conv_sessions = await db.execute(
        select(func.count())
        .select_from(LanguageSpeakingConversationSession)
        .where(
            LanguageSpeakingConversationSession.student_id == student_id,
            LanguageSpeakingConversationSession.language_id == language_id,
            LanguageSpeakingConversationSession.status == "ended",
        )
    )
    total_conversations = int(conv_sessions.scalar() or 0)

    speaking_q = await db.execute(
        select(func.count())
        .select_from(LanguageSpeakingProgress)
        .where(
            LanguageSpeakingProgress.student_id == student_id,
            LanguageSpeakingProgress.completed_at.isnot(None),
        )
    )
    total_speaking = int(speaking_q.scalar() or 0)

    writing_q = await db.execute(
        select(func.count())
        .select_from(LanguageWritingProgress)
        .where(
            LanguageWritingProgress.student_id == student_id,
            LanguageWritingProgress.completed_at.isnot(None),
        )
    )
    total_writing = int(writing_q.scalar() or 0)

    duration_q = await db.execute(
        select(func.coalesce(func.sum(LanguageActivityLog.duration_seconds), 0)).where(
            LanguageActivityLog.student_id == student_id,
            LanguageActivityLog.language_id == language_id,
        )
    )
    total_study_seconds = int(duration_q.scalar() or 0)

    overview = await build_curriculum_overview(db, student_id=student_id)
    objectives = overview.get("objectives") or []
    completed_objectives = sum(1 for o in objectives if o.get("status") in ("in_progress", "mastered"))
    mastered_objectives = sum(1 for o in objectives if o.get("status") == "mastered")

    scenario_q = await db.execute(
        select(func.count())
        .select_from(LanguageScenarioProgress)
        .where(
            LanguageScenarioProgress.student_id == student_id,
            LanguageScenarioProgress.language_id == language_id,
            LanguageScenarioProgress.status == "completed",
        )
    )
    scenarios_completed = int(scenario_q.scalar() or 0)

    return {
        "total_conversations": total_conversations,
        "total_speaking_submissions": total_speaking,
        "total_writing_submissions": total_writing,
        "total_study_minutes": int(round(total_study_seconds / 60)),
        "total_study_seconds": total_study_seconds,
        "completed_objectives": completed_objectives,
        "mastered_objectives": mastered_objectives,
        "objectives_total": len(objectives),
        "scenarios_completed": scenarios_completed,
    }


async def compute_improvement_trend(
    db: AsyncSession, *, student_id: int, language_id: int
) -> dict:
    """Compare average scores from recent vs prior week activity."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    recent_rows = await db.execute(
        select(LanguageActivityLog.payload_json, LanguageActivityLog.created_at)
        .where(
            LanguageActivityLog.student_id == student_id,
            LanguageActivityLog.language_id == language_id,
            LanguageActivityLog.created_at >= week_ago,
        )
        .order_by(LanguageActivityLog.created_at.desc())
    )
    prior_rows = await db.execute(
        select(LanguageActivityLog.payload_json, LanguageActivityLog.created_at)
        .where(
            LanguageActivityLog.student_id == student_id,
            LanguageActivityLog.language_id == language_id,
            LanguageActivityLog.created_at >= two_weeks_ago,
            LanguageActivityLog.created_at < week_ago,
        )
    )

    def _avg(rows) -> float | None:
        scores = []
        for payload, _ in rows.all():
            s = _avg_score_from_payload(payload)
            if s is not None:
                scores.append(s)
        return round(sum(scores) / len(scores), 1) if scores else None

    recent_avg = _avg(recent_rows)
    prior_avg = _avg(prior_rows)
    delta = None
    direction = "stable"
    if recent_avg is not None and prior_avg is not None:
        delta = round(recent_avg - prior_avg, 1)
        if delta >= 3:
            direction = "improving"
        elif delta <= -3:
            direction = "declining"

    return {
        "recent_week_average": recent_avg,
        "prior_week_average": prior_avg,
        "delta": delta,
        "direction": direction,
        "direction_ar": {
            "improving": "تحسّن",
            "declining": "انخفاض",
            "stable": "مستقر",
        }.get(direction, "مستقر"),
    }


async def list_scenario_progress(
    db: AsyncSession, *, student_id: int, language_id: int
) -> list[dict]:
    rows = await db.execute(
        select(LanguageScenarioProgress)
        .where(
            LanguageScenarioProgress.student_id == student_id,
            LanguageScenarioProgress.language_id == language_id,
        )
        .order_by(LanguageScenarioProgress.last_played_at.desc().nullslast())
    )
    out = []
    for row in rows.scalars().all():
        out.append(
            {
                "scenario_key": row.scenario_key,
                "scenario_id": row.scenario_id,
                "status": row.status,
                "completion_count": int(row.completion_count or 0),
                "best_score": int(row.best_score or 0),
                "best_scores": row.best_scores_json or {},
                "last_played_at": row.last_played_at,
                "first_completed_at": row.first_completed_at,
                "mastery_label_ar": _mastery_label(row),
            }
        )
    return out


def _mastery_label(row: LanguageScenarioProgress) -> str:
    count = int(row.completion_count or 0)
    best = int(row.best_score or 0)
    if count == 0:
        return "لم يبدأ"
    if count >= 3 and best >= 80:
        return "متقن"
    if count >= 1 and best >= 70:
        return "جيد"
    return "قيد التمرين"


async def refresh_statistics_on_analytics(
    db: AsyncSession, *, student_id: int, language_id: int
) -> dict:
    stats = await compute_language_statistics(db, student_id=student_id, language_id=language_id)
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics:
        analytics.statistics_json = stats
        await db.flush()
    return stats
