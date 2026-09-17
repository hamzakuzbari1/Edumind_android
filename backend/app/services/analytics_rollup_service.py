"""Precomputed analytics rollups — refresh via background job, not per HTTP request."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import CourseAnalytics, StudentAnalytics, TeacherAnalytics
from app.models.catalog import Course
from app.models.enrollment import PaymentStatus, StudentCourseAccess
from app.models.lesson import Lesson
from app.models.progress import StudentLessonProgress
from app.models.student_grade_report import StudentGradeReport


async def refresh_course_analytics(db: AsyncSession, course_id: int) -> CourseAnalytics:
    row = await db.get(CourseAnalytics, course_id)
    if not row:
        row = CourseAnalytics(course_id=course_id)
        db.add(row)

    student_count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(StudentCourseAccess)
                .where(
                    StudentCourseAccess.course_id == course_id,
                    StudentCourseAccess.payment_status == PaymentStatus.paid,
                )
            )
        ).scalar_one()
        or 0
    )
    total_lessons = int(
        (
            await db.execute(
                select(func.count()).select_from(Lesson).where(Lesson.course_id == course_id)
            )
        ).scalar_one()
        or 0
    )
    if total_lessons and student_count:
        completed_pairs = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(StudentLessonProgress)
                    .join(Lesson, Lesson.id == StudentLessonProgress.lesson_id)
                    .where(Lesson.course_id == course_id)
                )
            ).scalar_one()
            or 0
        )
        denom = total_lessons * student_count
        row.completion_rate = round((completed_pairs / denom) * 100, 2) if denom else 0.0
    else:
        row.completion_rate = 0.0

    avg_score = (
        await db.execute(
            select(func.avg(StudentGradeReport.average_score)).where(
                StudentGradeReport.course_id == course_id
            )
        )
    ).scalar_one()
    row.average_quiz_score = round(float(avg_score), 2) if avg_score is not None else None
    row.student_count = student_count
    row.active_students = student_count
    row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return row


async def refresh_teacher_analytics(db: AsyncSession, teacher_profile_id: int) -> TeacherAnalytics:
    row = await db.get(TeacherAnalytics, teacher_profile_id)
    if not row:
        row = TeacherAnalytics(teacher_profile_id=teacher_profile_id)
        db.add(row)

    courses = (
        await db.execute(select(Course.id).where(Course.teacher_profile_id == teacher_profile_id))
    ).scalars().all()
    row.total_courses = len(courses)

    if courses:
        paid_students = (
            await db.execute(
                select(func.count(func.distinct(StudentCourseAccess.student_id)))
                .select_from(StudentCourseAccess)
                .where(
                    StudentCourseAccess.course_id.in_(courses),
                    StudentCourseAccess.payment_status == PaymentStatus.paid,
                )
            )
        ).scalar_one()
    else:
        paid_students = 0
    row.total_students = int(paid_students or 0)

    if courses:
        avg_completion = (
            await db.execute(
                select(func.avg(CourseAnalytics.completion_rate)).where(
                    CourseAnalytics.course_id.in_(courses)
                )
            )
        ).scalar_one()
        row.average_completion = round(float(avg_completion), 2) if avg_completion else 0.0
    else:
        row.average_completion = 0.0

    row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return row


async def refresh_student_analytics(db: AsyncSession, student_id: int) -> StudentAnalytics:
    row = await db.get(StudentAnalytics, student_id)
    if not row:
        row = StudentAnalytics(student_id=student_id)
        db.add(row)

    avg_completion = (
        await db.execute(
            select(func.avg(StudentGradeReport.completion_percentage)).where(
                StudentGradeReport.student_id == student_id
            )
        )
    ).scalar_one()
    row.completion_rate = round(float(avg_completion), 2) if avg_completion is not None else 0.0

    avg_score = (
        await db.execute(
            select(func.avg(StudentGradeReport.average_score)).where(
                StudentGradeReport.student_id == student_id
            )
        )
    ).scalar_one()
    row.average_score = round(float(avg_score), 2) if avg_score is not None else None
    row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return row
