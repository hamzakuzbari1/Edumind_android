"""Real platform academic statistics for teacher portfolio."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import CourseAnalytics
from app.models.catalog import Course
from app.models.enrollment import PaymentStatus, StudentCourseAccess
from app.models.lesson import Lesson
from app.schemas.teacher_portfolio import TeacherAcademicStatisticsOut
from app.services.analytics_rollup_service import refresh_teacher_analytics
from app.services.subscription_access_service import is_access_active


async def build_teacher_academic_statistics(
    db: AsyncSession, teacher_profile_id: int
) -> TeacherAcademicStatisticsOut:
    await refresh_teacher_analytics(db, teacher_profile_id)

    course_rows = (
        await db.execute(
            select(Course.id).where(
                Course.teacher_profile_id == teacher_profile_id,
                Course.is_active.is_(True),
                Course.is_published.is_(True),
            )
        )
    ).scalars().all()
    course_ids = list(course_rows)
    courses_published = len(course_ids)

    lessons_published = 0
    if course_ids:
        lessons_published = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(Lesson)
                    .where(Lesson.course_id.in_(course_ids), Lesson.is_visible.is_(True))
                )
            ).scalar_one()
            or 0
        )

    total_students = 0
    active_students = 0
    if course_ids:
        access_rows = (
            await db.execute(
                select(StudentCourseAccess).where(
                    StudentCourseAccess.course_id.in_(course_ids),
                    StudentCourseAccess.payment_status == PaymentStatus.paid,
                )
            )
        ).scalars().all()
        seen: set[int] = set()
        active_seen: set[int] = set()
        for row in access_rows:
            seen.add(row.student_id)
            if is_access_active(row):
                active_seen.add(row.student_id)
        total_students = len(seen)
        active_students = len(active_seen)

    avg_completion = 0.0
    avg_quiz: float | None = None
    if course_ids:
        analytics = (
            await db.execute(
                select(CourseAnalytics).where(CourseAnalytics.course_id.in_(course_ids))
            )
        ).scalars().all()
        if analytics:
            avg_completion = round(
                sum(float(a.completion_rate or 0) for a in analytics) / len(analytics), 2
            )
            quiz_scores = [float(a.average_quiz_score) for a in analytics if a.average_quiz_score is not None]
            if quiz_scores:
                avg_quiz = round(sum(quiz_scores) / len(quiz_scores), 2)

    return TeacherAcademicStatisticsOut(
        active_students=active_students,
        total_students=total_students,
        courses_published=courses_published,
        lessons_published=lessons_published,
        average_lesson_completion_rate=avg_completion,
        average_quiz_score=avg_quiz,
    )
