"""Language achievement unlock checks and listing."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.achievement import LanguageStudentAchievement
from app.models.language.engagement import LanguageActivityLog, LanguageStreak
from app.models.language.scenario_progress import LanguageScenarioProgress
from app.services.language_achievement_registry import (
    LANGUAGE_ACHIEVEMENT_REGISTRY,
    SCENARIO_ACHIEVEMENT_MAP,
    SPEAKING_MASTER_GROWTH,
    VOCABULARY_EXPERT_GROWTH,
    VOCABULARY_EXPERT_KNOWN,
    WRITING_MASTER_GROWTH,
)
from app.services.language_analytics_service import refresh_language_analytics


async def _has_achievement(
    db: AsyncSession, *, student_id: int, language_id: int, key: str
) -> bool:
    row = await db.execute(
        select(LanguageStudentAchievement.id).where(
            LanguageStudentAchievement.student_id == student_id,
            LanguageStudentAchievement.language_id == language_id,
            LanguageStudentAchievement.achievement_key == key,
        )
    )
    return row.scalar_one_or_none() is not None


async def unlock_achievement(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    achievement_key: str,
) -> LanguageStudentAchievement | None:
    if achievement_key not in LANGUAGE_ACHIEVEMENT_REGISTRY:
        return None
    if await _has_achievement(db, student_id=student_id, language_id=language_id, key=achievement_key):
        return None
    row = LanguageStudentAchievement(
        student_id=student_id,
        language_id=language_id,
        achievement_key=achievement_key,
        unlocked_at=datetime.now(timezone.utc),
    )
    db.add(row)
    await db.flush()
    return row


async def record_scenario_completion(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    scenario_key: str,
    scenario_id: int | None = None,
    scores: dict | None = None,
) -> LanguageScenarioProgress:
    """Update scenario progress — callable from scenario end without modifying scenario service internals."""
    now = datetime.now(timezone.utc)
    avg_score = 0
    if scores:
        vals = [float(v) for v in scores.values() if v is not None]
        avg_score = int(round(sum(vals) / len(vals))) if vals else 0

    result = await db.execute(
        select(LanguageScenarioProgress).where(
            LanguageScenarioProgress.student_id == student_id,
            LanguageScenarioProgress.language_id == language_id,
            LanguageScenarioProgress.scenario_key == scenario_key,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = LanguageScenarioProgress(
            student_id=student_id,
            language_id=language_id,
            scenario_key=scenario_key,
            scenario_id=scenario_id,
            status="in_progress",
        )
        db.add(row)

    row.last_played_at = now
    row.scenario_id = scenario_id or row.scenario_id
    row.completion_count = int(row.completion_count or 0) + 1
    row.status = "completed"
    if not row.first_completed_at:
        row.first_completed_at = now
    if avg_score > int(row.best_score or 0):
        row.best_score = avg_score
        row.best_scores_json = scores
    await db.flush()
    return row


async def evaluate_achievements_for_event(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    event_type: str,
    payload_json: dict | None = None,
) -> list[str]:
    """Check and unlock achievements after an activity event. Returns newly unlocked keys."""
    payload = payload_json or {}
    unlocked: list[str] = []

    async def _try(key: str) -> None:
        row = await unlock_achievement(
            db, student_id=student_id, language_id=language_id, achievement_key=key
        )
        if row:
            unlocked.append(key)

    if event_type == "speaking_conversation_turn":
        await _try("first_conversation")

    if event_type in ("speaking_completed", "speaking_submitted"):
        await _try("first_speaking_exercise")

    if event_type in ("writing_completed", "writing_submitted"):
        await _try("first_writing_exercise")

    if event_type == "promotion_test_attempt" and payload.get("promoted"):
        await _try("first_promotion")

    if event_type == "scenario_complete":
        scenario_key = str(payload.get("scenario_key") or payload.get("category") or "")
        scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else None
        await record_scenario_completion(
            db,
            student_id=student_id,
            language_id=language_id,
            scenario_key=scenario_key,
            scenario_id=payload.get("scenario_id"),
            scores=scores,
        )
        ach = SCENARIO_ACHIEVEMENT_MAP.get(scenario_key)
        if ach:
            await _try(ach)

    streak = await db.execute(
        select(LanguageStreak).where(
            LanguageStreak.student_id == student_id,
            LanguageStreak.language_id == language_id,
        )
    )
    st = streak.scalar_one_or_none()
    if st:
        if int(st.current_streak or 0) >= 7:
            await _try("streak_7")
        if int(st.current_streak or 0) >= 30:
            await _try("streak_30")

    analytics = await refresh_language_analytics(db, student_id=student_id, language_id=language_id)
    growth = analytics.skill_growth_json or {}
    speaking_g = int((growth.get("speaking") or {}).get("growth_percent") or 0)
    writing_g = int((growth.get("writing") or {}).get("growth_percent") or 0)
    vocab = growth.get("vocabulary") or {}
    vocab_known = int(vocab.get("known_words") or 0)
    vocab_growth = int(vocab.get("growth_percent") or 0)

    if speaking_g >= SPEAKING_MASTER_GROWTH:
        await _try("speaking_master")
    if writing_g >= WRITING_MASTER_GROWTH:
        await _try("writing_master")
    if vocab_known >= VOCABULARY_EXPERT_KNOWN or vocab_growth >= VOCABULARY_EXPERT_GROWTH:
        await _try("vocabulary_expert")

    return unlocked


async def list_student_achievements(
    db: AsyncSession, *, student_id: int, language_id: int
) -> dict:
    earned_rows = await db.execute(
        select(LanguageStudentAchievement).where(
            LanguageStudentAchievement.student_id == student_id,
            LanguageStudentAchievement.language_id == language_id,
        )
    )
    earned_map = {r.achievement_key: r for r in earned_rows.scalars().all()}

    items = []
    for key, meta in LANGUAGE_ACHIEVEMENT_REGISTRY.items():
        earned = earned_map.get(key)
        items.append(
            {
                "key": key,
                "icon": meta["icon"],
                "title_ar": meta["title_ar"],
                "title_en": meta["title_en"],
                "description_ar": meta["description_ar"],
                "category": meta["category"],
                "earned": earned is not None,
                "unlocked_at": earned.unlocked_at if earned else None,
            }
        )
    earned_count = sum(1 for i in items if i["earned"])
    return {
        "achievements": items,
        "earned_count": earned_count,
        "total_count": len(items),
    }


async def count_earned_achievements(db: AsyncSession, *, student_id: int, language_id: int) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(LanguageStudentAchievement)
        .where(
            LanguageStudentAchievement.student_id == student_id,
            LanguageStudentAchievement.language_id == language_id,
        )
    )
    return int(result.scalar() or 0)
