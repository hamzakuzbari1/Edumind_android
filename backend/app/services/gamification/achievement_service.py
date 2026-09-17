"""Achievement definitions and unlock logic."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.gamification.achievement_registry import ACHIEVEMENT_REGISTRY, LEGACY_KEY_ALIASES
from app.services.gamification.guards import is_missing_gamification_table, log_missing_tables

from app.models.course_quiz import CourseQuizAttempt, CourseQuizAttemptStatus
from app.models.progress import StudentLessonProgress
from app.models.quiz import QuizAttempt
from app.models.student_gamification import StudentAchievement
from app.models.student_study_streak import StudentStudyStreak

async def list_achievements(db: AsyncSession, student_id: int) -> list[dict]:
    try:
        result = await db.execute(
            select(StudentAchievement)
            .where(StudentAchievement.student_id == student_id)
            .order_by(StudentAchievement.unlocked_at.desc())
        )
        rows = []
        for row in result.scalars().all():
            key = row.achievement_key
            if key in ACHIEVEMENT_REGISTRY:
                meta = ACHIEVEMENT_REGISTRY[key]
            elif key in LEGACY_KEY_ALIASES:
                key = LEGACY_KEY_ALIASES[key]
                meta = ACHIEVEMENT_REGISTRY[key]
            else:
                meta = {"icon": row.icon, "title": row.title, "description": row.description}
            rows.append(
                {
                    "achievement_key": key,
                    "icon": meta["icon"],
                    "title": meta["title"],
                    "description": meta["description"],
                    "unlocked_at": row.unlocked_at.isoformat() if row.unlocked_at else None,
                }
            )
        return rows
    except (ProgrammingError, DBAPIError) as exc:
        if is_missing_gamification_table(exc):
            log_missing_tables("achievement list")
            return []
        raise


async def get_achievement_catalog(db: AsyncSession, student_id: int) -> list[dict]:
    await sync_achievement_progress(db, student_id)
    unlocked = {a["achievement_key"]: a for a in await list_achievements(db, student_id)}
    catalog = []
    for key, meta in ACHIEVEMENT_REGISTRY.items():
        row = unlocked.get(key)
        catalog.append(
            {
                "achievement_key": key,
                "icon": meta["icon"],
                "title": meta["title"],
                "description": meta["description"],
                "unlocked": row is not None,
                "unlocked_at": row.get("unlocked_at") if row else None,
            }
        )
    return catalog


async def unlock_achievement(db: AsyncSession, student_id: int, key: str) -> dict | None:
    if key not in ACHIEVEMENT_REGISTRY:
        return None
    try:
        existing = await db.execute(
            select(StudentAchievement).where(
                StudentAchievement.student_id == student_id,
                StudentAchievement.achievement_key == key,
            )
        )
        if existing.scalar_one_or_none():
            return None
        meta = ACHIEVEMENT_REGISTRY[key]
        row = StudentAchievement(
            student_id=student_id,
            achievement_key=key,
            icon=meta["icon"],
            title=meta["title"],
            description=meta["description"],
            unlocked_at=datetime.now(timezone.utc),
        )
        db.add(row)
        await db.flush()
        return {
            "achievement_key": key,
            "icon": meta["icon"],
            "title": meta["title"],
            "description": meta["description"],
            "unlocked_at": row.unlocked_at.isoformat(),
        }
    except (ProgrammingError, DBAPIError) as exc:
        if is_missing_gamification_table(exc):
            log_missing_tables("achievement unlock")
            return None
        raise


async def _lesson_count(db: AsyncSession, student_id: int) -> int:
    result = await db.execute(
        select(func.count()).select_from(StudentLessonProgress).where(
            StudentLessonProgress.student_id == student_id,
            StudentLessonProgress.completed_at.is_not(None),
        )
    )
    return int(result.scalar_one() or 0)


async def _average_quiz_score(db: AsyncSession, student_id: int) -> int | None:
    scores: list[int] = []

    lesson_attempts = await db.execute(
        select(QuizAttempt.correct_count, QuizAttempt.feedback_json).where(
            QuizAttempt.student_id == student_id
        )
    )
    for correct, feedback_json in lesson_attempts.all():
        import json

        total = 0
        if feedback_json:
            try:
                total = len(json.loads(feedback_json))
            except Exception:
                pass
        if not total:
            total = max(correct, 1)
        scores.append(round((correct / total) * 100) if total else 0)

    manual = await db.execute(
        select(CourseQuizAttempt.percent).where(
            CourseQuizAttempt.student_id == student_id,
            CourseQuizAttempt.status.in_(
                [CourseQuizAttemptStatus.submitted, CourseQuizAttemptStatus.graded]
            ),
        )
    )
    for (pct,) in manual.all():
        if pct is not None:
            scores.append(round(float(pct)))

    if not scores:
        return None
    return round(sum(scores) / len(scores))


async def sync_achievement_progress(db: AsyncSession, student_id: int) -> None:
    count = await _lesson_count(db, student_id)
    if count >= 1:
        await unlock_achievement(db, student_id, "first_lesson")
    if count >= 10:
        await unlock_achievement(db, student_id, "lessons_10")
    if count >= 100:
        await unlock_achievement(db, student_id, "lessons_100")

    avg = await _average_quiz_score(db, student_id)
    if avg is not None and avg >= 95:
        await unlock_achievement(db, student_id, "average_score_95")

    streak_result = await db.execute(
        select(StudentStudyStreak).where(StudentStudyStreak.student_id == student_id)
    )
    streak_row = streak_result.scalar_one_or_none()
    if streak_row and streak_row.current_streak_days >= 30:
        await unlock_achievement(db, student_id, "streak_30")


async def check_after_lesson(db: AsyncSession, student_id: int) -> None:
    count = await _lesson_count(db, student_id)
    if count >= 1:
        await unlock_achievement(db, student_id, "first_lesson")
    if count >= 10:
        await unlock_achievement(db, student_id, "lessons_10")
    if count >= 100:
        await unlock_achievement(db, student_id, "lessons_100")


async def check_after_quiz(db: AsyncSession, student_id: int, score_percent: int) -> None:
    avg = await _average_quiz_score(db, student_id)
    if avg is not None and avg >= 95:
        await unlock_achievement(db, student_id, "average_score_95")


async def check_after_course_complete(db: AsyncSession, student_id: int) -> None:
    await unlock_achievement(db, student_id, "first_course_completed")


async def check_streak_milestones(db: AsyncSession, student_id: int, streak_days: int) -> None:
    if streak_days >= 30:
        await unlock_achievement(db, student_id, "streak_30")
