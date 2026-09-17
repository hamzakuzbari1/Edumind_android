"""Study day and task streak tracking."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student_study_streak import StudentStudyStreak


async def get_or_create_streak(db: AsyncSession, student_id: int) -> StudentStudyStreak:
    result = await db.execute(
        select(StudentStudyStreak).where(StudentStudyStreak.student_id == student_id)
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    row = StudentStudyStreak(student_id=student_id)
    db.add(row)
    await db.flush()
    return row


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _is_consecutive(prev: date | None, today: date) -> bool:
    if prev is None:
        return False
    return (today - prev).days == 1


async def record_study_activity(db: AsyncSession, student_id: int) -> tuple[StudentStudyStreak, bool]:
    """Call when student completes a planner task or meaningful study action."""
    streak = await get_or_create_streak(db, student_id)
    today = _today()
    new_study_day = False

    if streak.last_study_date != today:
        new_study_day = True
        if _is_consecutive(streak.last_study_date, today):
            streak.current_streak_days += 1
        elif streak.last_study_date is None:
            streak.current_streak_days = 1
        else:
            streak.current_streak_days = 1
        streak.last_study_date = today
        streak.longest_streak_days = max(streak.longest_streak_days, streak.current_streak_days)

    if streak.last_task_date != today:
        if _is_consecutive(streak.last_task_date, today):
            streak.task_streak_days += 1
        elif streak.last_task_date is None:
            streak.task_streak_days = 1
        else:
            streak.task_streak_days = 1
        streak.last_task_date = today

    await db.flush()
    return streak, new_study_day


def streak_to_dict(streak: StudentStudyStreak) -> dict:
    return {
        "current_streak_days": streak.current_streak_days,
        "longest_streak_days": streak.longest_streak_days,
        "task_streak_days": streak.task_streak_days,
        "last_study_date": streak.last_study_date.isoformat() if streak.last_study_date else None,
    }
