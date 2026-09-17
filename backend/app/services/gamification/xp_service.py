"""Award XP for meaningful learning actions only."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson import ContentChunk, Lesson
from app.models.planner import PlannerScheduleSlot, ScheduleSlotStatus
from app.models.progress import StudentLessonProgress
from app.models.student_gamification import StudentXp
from app.models.student_study_streak import StudentStudyStreak
from app.services.gamification import achievement_service
from app.services.gamification.guards import (
    empty_gamification_profile,
    is_missing_gamification_table,
    log_missing_tables,
)
from app.services.gamification.xp_activity import build_recent_xp_activity
from app.services.gamification.xp_levels import level_progress, xp_to_level
from app.services.gamification.xp_rules import get_xp_rules
from app.services.student_courses_service import _completed_lesson_ids, _course_lessons

MODULE_BATCH_SIZE = 5
LONG_LESSON_MIN_PAGES = 10
LONG_LESSON_MIN_CHUNKS = 8

XP_LESSON = 20
XP_LONG_LESSON = 35
XP_MODULE = 100
XP_COURSE = 500
XP_QUIZ_BASE = 30
XP_QUIZ_80 = 20
XP_QUIZ_90 = 40
XP_QUIZ_100 = 75
XP_PLANNER_TASK = 15
XP_PLANNER_DAY = 75
XP_PLANNER_WEEK = 250
XP_STUDY_DAY = 10
XP_STREAK_7 = 100
XP_STREAK_14 = 250
XP_STREAK_30 = 750


async def get_or_create_xp_row(db: AsyncSession, student_id: int) -> StudentXp:
    result = await db.execute(select(StudentXp).where(StudentXp.student_id == student_id))
    row = result.scalar_one_or_none()
    if row:
        return row
    row = StudentXp(student_id=student_id, total_xp=0, level=1, awarded_keys_json="[]")
    db.add(row)
    await db.flush()
    return row


def _load_keys(row: StudentXp) -> set[str]:
    try:
        return set(json.loads(row.awarded_keys_json or "[]"))
    except Exception:
        return set()


def _save_keys(row: StudentXp, keys: set[str]) -> None:
    row.awarded_keys_json = json.dumps(sorted(keys), ensure_ascii=False)


async def award_xp(db: AsyncSession, student_id: int, amount: int, key: str) -> int:
    """Idempotent XP award. Returns XP actually granted (0 if duplicate)."""
    if amount <= 0:
        return 0
    try:
        row = await get_or_create_xp_row(db, student_id)
        keys = _load_keys(row)
        if key in keys:
            return 0
        keys.add(key)
        row.total_xp += amount
        row.level = xp_to_level(row.total_xp)
        _save_keys(row, keys)
        await db.flush()
        return amount
    except (ProgrammingError, DBAPIError) as exc:
        if is_missing_gamification_table(exc):
            log_missing_tables("XP award")
            return 0
        raise


def _quiz_bonus(score_percent: int) -> int:
    if score_percent >= 100:
        return XP_QUIZ_100
    if score_percent >= 90:
        return XP_QUIZ_90
    if score_percent >= 80:
        return XP_QUIZ_80
    return 0


async def _is_long_lesson(db: AsyncSession, lesson: Lesson) -> bool:
    if lesson.page_count and lesson.page_count >= LONG_LESSON_MIN_PAGES:
        return True
    if lesson.video_url and lesson.pdf_path:
        return True
    chunk_count = await db.scalar(
        select(func.count()).select_from(ContentChunk).where(ContentChunk.lesson_id == lesson.id)
    )
    return int(chunk_count or 0) >= LONG_LESSON_MIN_CHUNKS


async def _check_course_milestones(db: AsyncSession, student_id: int, course_id: int | None) -> None:
    if not course_id:
        return
    lessons = await _course_lessons(db, course_id)
    visible = [l for l in lessons if l.is_visible]
    if not visible:
        return
    lesson_ids = [l.id for l in visible]
    completed = await _completed_lesson_ids(db, student_id, lesson_ids)
    sorted_lessons = sorted(visible, key=lambda l: (l.sort_order, l.id))

    for batch_idx in range(0, len(sorted_lessons), MODULE_BATCH_SIZE):
        batch = sorted_lessons[batch_idx : batch_idx + MODULE_BATCH_SIZE]
        if all(l.id in completed for l in batch):
            await award_xp(db, student_id, XP_MODULE, f"module:{course_id}:{batch_idx // MODULE_BATCH_SIZE}")

    if len(completed) >= len(visible):
        awarded = await award_xp(db, student_id, XP_COURSE, f"course:{course_id}")
        if awarded:
            await achievement_service.check_after_course_complete(db, student_id)


async def on_lesson_completed(db: AsyncSession, student_id: int, lesson_id: int) -> None:
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        return
    is_long = await _is_long_lesson(db, lesson)
    amount = XP_LONG_LESSON if is_long else XP_LESSON
    await award_xp(db, student_id, amount, f"lesson:{lesson_id}")
    await _check_course_milestones(db, student_id, lesson.course_id)
    await achievement_service.check_after_lesson(db, student_id)


async def on_lesson_quiz_submitted(
    db: AsyncSession, student_id: int, lesson_id: int, score_percent: int, attempt_id: int
) -> None:
    base = await award_xp(db, student_id, XP_QUIZ_BASE, f"lesson_quiz:{attempt_id}")
    if base:
        bonus = _quiz_bonus(score_percent)
        if bonus:
            await award_xp(db, student_id, bonus, f"lesson_quiz_bonus:{attempt_id}")
    await achievement_service.check_after_quiz(db, student_id, score_percent)


async def on_manual_quiz_submitted(
    db: AsyncSession, student_id: int, attempt_id: int, score_percent: int
) -> None:
    base = await award_xp(db, student_id, XP_QUIZ_BASE, f"manual_quiz:{attempt_id}")
    if base:
        bonus = _quiz_bonus(score_percent)
        if bonus:
            await award_xp(db, student_id, bonus, f"manual_quiz_bonus:{attempt_id}")
    await achievement_service.check_after_quiz(db, student_id, score_percent)


async def on_planner_task_completed(db: AsyncSession, student_id: int, slot_id: int) -> None:
    await award_xp(db, student_id, XP_PLANNER_TASK, f"planner_task:{slot_id}")
    await _check_planner_day_complete(db, student_id)
    await _check_planner_week_complete(db, student_id)


async def _check_planner_day_complete(db: AsyncSession, student_id: int) -> None:
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    result = await db.execute(
        select(PlannerScheduleSlot).where(
            PlannerScheduleSlot.student_id == student_id,
            PlannerScheduleSlot.scheduled_at >= start,
            PlannerScheduleSlot.scheduled_at < end,
        )
    )
    slots = list(result.scalars().all())
    planned = [s for s in slots if s.status in (ScheduleSlotStatus.planned, ScheduleSlotStatus.completed, ScheduleSlotStatus.missed)]
    if not planned:
        return
    if all(s.status == ScheduleSlotStatus.completed for s in planned):
        day_key = today.isoformat()
        await award_xp(db, student_id, XP_PLANNER_DAY, f"planner_day:{day_key}")


async def _check_planner_week_complete(db: AsyncSession, student_id: int) -> None:
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)
    iso_week = week_start.date().isocalendar()
    week_key = f"{iso_week.year}-W{iso_week.week:02d}"

    result = await db.execute(
        select(PlannerScheduleSlot).where(
            PlannerScheduleSlot.student_id == student_id,
            PlannerScheduleSlot.scheduled_at >= week_start,
            PlannerScheduleSlot.scheduled_at < week_end,
            PlannerScheduleSlot.status != ScheduleSlotStatus.missed,
        )
    )
    slots = list(result.scalars().all())
    if len(slots) < 2:
        return
    if all(s.status == ScheduleSlotStatus.completed for s in slots):
        await award_xp(db, student_id, XP_PLANNER_WEEK, f"planner_week:{week_key}")


async def on_study_streak_updated(
    db: AsyncSession, student_id: int, streak: StudentStudyStreak, *, new_study_day: bool
) -> None:
    if new_study_day:
        day_key = streak.last_study_date.isoformat() if streak.last_study_date else _today_iso()
        await award_xp(db, student_id, XP_STUDY_DAY, f"study_day:{day_key}")

    days = streak.current_streak_days
    if days >= 7:
        await award_xp(db, student_id, XP_STREAK_7, "streak_milestone:7")
    if days >= 14:
        await award_xp(db, student_id, XP_STREAK_14, "streak_milestone:14")
    if days >= 30:
        await award_xp(db, student_id, XP_STREAK_30, "streak_milestone:30")
    await achievement_service.check_streak_milestones(db, student_id, days)


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


async def get_gamification_profile(db: AsyncSession, student_id: int) -> dict:
    current_streak = 0
    longest_streak = 0
    try:
        streak_result = await db.execute(
            select(StudentStudyStreak).where(StudentStudyStreak.student_id == student_id)
        )
        streak_row = streak_result.scalar_one_or_none()
        if streak_row:
            current_streak = streak_row.current_streak_days
            longest_streak = streak_row.longest_streak_days
    except (ProgrammingError, DBAPIError):
        pass

    try:
        row = await get_or_create_xp_row(db, student_id)
        progress = level_progress(row.total_xp)
        achievements = await achievement_service.list_achievements(db, student_id)
        badges = await achievement_service.get_achievement_catalog(db, student_id)
        recent_activity = build_recent_xp_activity(row.awarded_keys_json, achievements)
        return {
            "level": progress["level"],
            "total_xp": progress["total_xp"],
            "xp_to_next_level": progress["xp_to_next_level"],
            "xp_in_level": progress["xp_in_level"],
            "xp_for_level": progress["xp_for_level"],
            "progress_percent": progress["progress_percent"],
            "is_max_level": progress["is_max_level"],
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "achievements": achievements,
            "achievement_count": len(achievements),
            "streak_display": f"🔥 {current_streak} يوم" if current_streak else "🔥 0 يوم",
            "badges": badges,
            "xp_rules": get_xp_rules(),
            "recent_activity": recent_activity,
        }
    except (ProgrammingError, DBAPIError) as exc:
        if is_missing_gamification_table(exc):
            log_missing_tables("gamification profile")
            return empty_gamification_profile(
                current_streak=current_streak,
                longest_streak=longest_streak,
            )
        raise
