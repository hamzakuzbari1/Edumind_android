"""Phase 11 — Analytics dashboard backend (time-series over daily snapshots).

Records an idempotent daily snapshot of the learner's state and serves time-series in a standard
envelope: {metric, period, data_points:[{date, value, numeric}], summary:{start, current, change, trend}}.
Reuses existing data (analytics, pronunciation scores, error patterns); only adds the snapshots table.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.analytics import LanguageAnalytics
from app.models.language.error_pattern import LanguageErrorPattern
from app.models.language.pronunciation import LanguagePronunciationScore
from app.models.language.snapshot import LanguageProgressSnapshot
from app.services.language_level_utils import CEFR_RANK, RANK_CEFR


# --------------------------------------------------------------------------------------------------
# Pure helpers (no I/O — unit-tested directly)
# --------------------------------------------------------------------------------------------------
def rank_to_cefr(rank: int) -> str | None:
    return RANK_CEFR[rank].value if rank in RANK_CEFR else None


def series_trend(values: list[float]) -> str:
    """improving | stable | worsening over an ordered (oldest..newest) numeric series."""
    nums = [float(v) for v in values if v is not None]
    if len(nums) < 2:
        return "stable"
    if nums[-1] - nums[0] > 0:
        return "improving"
    if nums[-1] - nums[0] < 0:
        return "worsening"
    return "stable"


def build_envelope(metric: str, period: str, data_points: list[dict]) -> dict:
    """Wrap data points (each {date, value, numeric}) in the standard analytics envelope."""
    numerics = [p["numeric"] for p in data_points if p.get("numeric") is not None]
    start = data_points[0] if data_points else None
    current = data_points[-1] if data_points else None
    change = None
    if start and current and start.get("numeric") is not None and current.get("numeric") is not None:
        change = round(current["numeric"] - start["numeric"], 2)
    return {
        "metric": metric,
        "period": period,
        "data_points": data_points,
        "summary": {
            "start": start["value"] if start else None,
            "current": current["value"] if current else None,
            "change": change,
            "trend": series_trend(numerics),
        },
    }


def _rank(level) -> int:
    return CEFR_RANK.get(level, 0) if level else 0


# --------------------------------------------------------------------------------------------------
# Snapshot writing
# --------------------------------------------------------------------------------------------------
async def record_snapshot(db: AsyncSession, *, student_id: int, language_id: int) -> None:
    """Upsert today's snapshot from current state (idempotent per day). Best-effort."""
    today = datetime.now(timezone.utc).date()
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics is None:
        return

    pron_avg = (
        await db.execute(
            select(func.avg(LanguagePronunciationScore.overall)).where(
                LanguagePronunciationScore.student_id == student_id,
                LanguagePronunciationScore.language_id == language_id,
            )
        )
    ).scalar_one_or_none()

    existing = (
        await db.execute(
            select(LanguageProgressSnapshot).where(
                LanguageProgressSnapshot.student_id == student_id,
                LanguageProgressSnapshot.language_id == language_id,
                LanguageProgressSnapshot.snapshot_date == today,
            )
        )
    ).scalar_one_or_none()

    # The most recent snapshot before today — to detect a CEFR level-up and record a milestone.
    prev_rank = (
        await db.execute(
            select(LanguageProgressSnapshot.overall_rank)
            .where(
                LanguageProgressSnapshot.student_id == student_id,
                LanguageProgressSnapshot.language_id == language_id,
                LanguageProgressSnapshot.snapshot_date < today,
            )
            .order_by(desc(LanguageProgressSnapshot.snapshot_date))
            .limit(1)
        )
    ).scalar_one_or_none()

    values = dict(
        overall_rank=_rank(analytics.overall_level_internal),
        reading_rank=_rank(analytics.reading_level),
        listening_rank=_rank(analytics.listening_level),
        writing_rank=_rank(analytics.writing_level),
        speaking_rank=_rank(analytics.speaking_level),
        xp_total=int(analytics.xp_total or 0),
        vocabulary_count=int(analytics.vocabulary_count or 0),
        pronunciation_avg=int(round(float(pron_avg))) if pron_avg is not None else 0,
    )
    if existing is not None:
        for k, v in values.items():
            setattr(existing, k, v)
    else:
        db.add(LanguageProgressSnapshot(student_id=student_id, language_id=language_id, snapshot_date=today, **values))
    await db.flush()

    # Phase 1 loop: a CEFR level-up becomes a learner-memory milestone (-> "Recent wins" in prompts).
    new_rank = values["overall_rank"]
    if prev_rank and new_rank and new_rank > prev_rank:
        try:
            from app.services.language_learner_memory_service import add_milestone

            await add_milestone(
                db, student_id=student_id, language_id=language_id,
                milestone=f"Reached {rank_to_cefr(new_rank)} (overall level)",
            )
        except Exception:  # never let milestone recording break snapshotting
            pass


# --------------------------------------------------------------------------------------------------
# Time-series reads
# --------------------------------------------------------------------------------------------------
async def _snapshots(db: AsyncSession, *, student_id: int, language_id: int, limit: int = 60) -> list[LanguageProgressSnapshot]:
    rows = (
        await db.execute(
            select(LanguageProgressSnapshot)
            .where(
                LanguageProgressSnapshot.student_id == student_id,
                LanguageProgressSnapshot.language_id == language_id,
            )
            .order_by(desc(LanguageProgressSnapshot.snapshot_date))
            .limit(limit)
        )
    ).scalars().all()
    return list(reversed(rows))  # oldest..newest


async def cefr_progress(db: AsyncSession, *, student_id: int, language_id: int) -> dict:
    rows = await _snapshots(db, student_id=student_id, language_id=language_id)
    points = [
        {"date": s.snapshot_date.isoformat(), "value": rank_to_cefr(s.overall_rank), "numeric": s.overall_rank}
        for s in rows if s.overall_rank
    ]
    return build_envelope("cefr_progress", "last_60_days", points)


async def vocabulary_growth(db: AsyncSession, *, student_id: int, language_id: int) -> dict:
    rows = await _snapshots(db, student_id=student_id, language_id=language_id)
    points = [
        {"date": s.snapshot_date.isoformat(), "value": s.vocabulary_count, "numeric": s.vocabulary_count}
        for s in rows
    ]
    return build_envelope("vocabulary_growth", "last_60_days", points)


async def xp_growth(db: AsyncSession, *, student_id: int, language_id: int) -> dict:
    rows = await _snapshots(db, student_id=student_id, language_id=language_id)
    points = [
        {"date": s.snapshot_date.isoformat(), "value": s.xp_total, "numeric": s.xp_total}
        for s in rows
    ]
    return build_envelope("xp_growth", "last_60_days", points)


async def pronunciation_progress(db: AsyncSession, *, student_id: int, language_id: int) -> dict:
    rows = await _snapshots(db, student_id=student_id, language_id=language_id)
    points = [
        {"date": s.snapshot_date.isoformat(), "value": s.pronunciation_avg, "numeric": s.pronunciation_avg}
        for s in rows if s.pronunciation_avg
    ]
    return build_envelope("pronunciation_progress", "last_60_days", points)


async def skill_breakdown(db: AsyncSession, *, student_id: int, language_id: int) -> dict:
    """Current per-skill CEFR (latest known)."""
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    skills = {}
    for skill in ("reading", "listening", "writing", "speaking"):
        lvl = getattr(analytics, f"{skill}_level", None) if analytics else None
        skills[skill] = {"value": lvl.value if lvl else None, "numeric": _rank(lvl)}
    return {"metric": "skill_breakdown", "skills": skills}


async def error_trends(db: AsyncSession, *, student_id: int, language_id: int) -> dict:
    """Total recurring-error load by type (current)."""
    rows = (
        await db.execute(
            select(LanguageErrorPattern.error_type, func.sum(LanguageErrorPattern.occurrence_count))
            .where(
                LanguageErrorPattern.student_id == student_id,
                LanguageErrorPattern.language_id == language_id,
            )
            .group_by(LanguageErrorPattern.error_type)
        )
    ).all()
    by_type = {t: int(c or 0) for t, c in rows}
    return {"metric": "error_trends", "by_type": by_type, "total": sum(by_type.values())}
