"""Activity log and streak updates for language learning."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.engagement import LanguageActivityLog, LanguageStreak
from app.models.language.enums import LanguageSkill, LanguageVocabularyStatus


async def record_activity(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    event_type: str,
    skill: LanguageSkill | None = None,
    duration_seconds: int = 0,
    payload_json: dict | None = None,
) -> LanguageActivityLog:
    row = LanguageActivityLog(
        student_id=student_id,
        language_id=language_id,
        event_type=event_type,
        skill=skill,
        duration_seconds=duration_seconds,
        payload_json=payload_json or {},
    )
    db.add(row)
    await db.flush()
    await update_streak(db, student_id=student_id, language_id=language_id)
    return row


async def update_streak(db: AsyncSession, *, student_id: int, language_id: int) -> LanguageStreak:
    today = date.today()
    result = await db.execute(
        select(LanguageStreak).where(
            LanguageStreak.student_id == student_id,
            LanguageStreak.language_id == language_id,
        )
    )
    streak = result.scalar_one_or_none()
    if not streak:
        streak = LanguageStreak(
            student_id=student_id,
            language_id=language_id,
            current_streak=1,
            longest_streak=1,
            last_activity_date=today,
        )
        db.add(streak)
        await db.flush()
        return streak

    last = streak.last_activity_date
    if last == today:
        return streak
    if last and (today - last).days == 1:
        streak.current_streak = int(streak.current_streak or 0) + 1
    else:
        streak.current_streak = 1
    streak.longest_streak = max(int(streak.longest_streak or 0), int(streak.current_streak))
    streak.last_activity_date = today
    await db.flush()
    return streak


async def upsert_vocabulary_from_lesson(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    lemmas: list[str],
) -> None:
    if not lemmas:
        return
    # Delegate to the spaced-repetition upsert so new lemmas are scheduled (next_review_at = now)
    # and existing rows keep their SM-2 state untouched.
    from app.services.language_vocabulary_sr_service import upsert_vocabulary_with_sr

    await upsert_vocabulary_with_sr(db, student_id=student_id, language_id=language_id, lemmas=lemmas)
