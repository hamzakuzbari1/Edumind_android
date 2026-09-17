"""Precomputed student_grade_reports for parent dashboards."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.attendance import AttendanceStatus, StudentAttendanceRecord
from app.models.catalog import Course
from app.models.course_quiz import CourseQuiz, CourseQuizAttempt
from app.models.enrollment import StudentCourseAccess
from app.models.lesson import Lesson
from app.models.progress import StudentLessonProgress
from app.models.student_grade_report import StudentGradeReport


async def refresh_student_grade_reports(db: AsyncSession, student_id: int) -> list[StudentGradeReport]:
    """Recompute rollup rows for all courses the student has access to."""
    access_result = await db.execute(
        select(StudentCourseAccess)
        .where(StudentCourseAccess.student_id == student_id)
        .options(selectinload(StudentCourseAccess.course).selectinload(Course.subject))
    )
    accesses = access_result.scalars().all()
    reports: list[StudentGradeReport] = []

    for access in accesses:
        course = access.course
        if not course:
            continue
        report = await _upsert_course_report(db, student_id, course.id)
        reports.append(report)

    await db.flush()
    return reports


def _grade_report_course_query(student_id: int):
    return (
        select(StudentGradeReport, Course)
        .join(Course, Course.id == StudentGradeReport.course_id)
        .where(StudentGradeReport.student_id == student_id)
        .options(selectinload(Course.subject))
        .order_by(Course.title)
    )


async def list_student_grade_reports(db: AsyncSession, student_id: int) -> list[dict]:
    """Return parent-facing course progress (refresh if empty)."""
    result = await db.execute(_grade_report_course_query(student_id))
    rows = result.all()
    if not rows:
        reports = await refresh_student_grade_reports(db, student_id)
        if not reports:
            return []
        result = await db.execute(_grade_report_course_query(student_id))
        rows = result.all()

    out: list[dict] = []
    for report, course in rows:
        out.append(
            {
                "course_id": course.id,
                "course_title": course.title,
                "subject_name": course.subject.name_ar if course.subject else "",
                "average_score": report.average_score,
                "attendance_percentage": report.attendance_percentage,
                "completion_percentage": report.completion_percentage,
                "updated_at": report.updated_at.isoformat() if report.updated_at else None,
            }
        )
    return out


async def _upsert_course_report(db: AsyncSession, student_id: int, course_id: int) -> StudentGradeReport:
    existing = await db.execute(
        select(StudentGradeReport).where(
            StudentGradeReport.student_id == student_id,
            StudentGradeReport.course_id == course_id,
        )
    )
    report = existing.scalar_one_or_none()
    if not report:
        report = StudentGradeReport(student_id=student_id, course_id=course_id)
        db.add(report)

    total_lessons = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Lesson)
                .where(Lesson.course_id == course_id, Lesson.is_visible.is_(True))
            )
        ).scalar_one()
        or 0
    )
    completed = int(
        (
            await db.execute(
                select(func.count())
                .select_from(StudentLessonProgress)
                .join(Lesson, Lesson.id == StudentLessonProgress.lesson_id)
                .where(
                    StudentLessonProgress.student_id == student_id,
                    Lesson.course_id == course_id,
                    StudentLessonProgress.completed_at.is_not(None),
                )
            )
        ).scalar_one()
        or 0
    )
    report.completion_percentage = (
        round((completed / total_lessons) * 100, 1) if total_lessons else 0.0
    )

    att_total = int(
        (
            await db.execute(
                select(func.count())
                .select_from(StudentAttendanceRecord)
                .where(StudentAttendanceRecord.student_id == student_id)
            )
        ).scalar_one()
        or 0
    )
    att_present = int(
        (
            await db.execute(
                select(func.count())
                .select_from(StudentAttendanceRecord)
                .where(
                    StudentAttendanceRecord.student_id == student_id,
                    StudentAttendanceRecord.status == AttendanceStatus.present,
                )
            )
        ).scalar_one()
        or 0
    )
    report.attendance_percentage = (
        round((att_present / att_total) * 100, 1) if att_total else None
    )

    quiz_avg = (
        await db.execute(
            select(func.avg(CourseQuizAttempt.percent))
            .select_from(CourseQuizAttempt)
            .join(CourseQuiz, CourseQuiz.id == CourseQuizAttempt.quiz_id)
            .where(
                CourseQuizAttempt.student_id == student_id,
                CourseQuiz.course_id == course_id,
                CourseQuizAttempt.percent.is_not(None),
            )
        )
    ).scalar_one()
    if quiz_avg is None:
        from app.models.quiz import QuizAttempt

        lesson_avg = (
            await db.execute(
                select(func.avg(QuizAttempt.correct_count))
                .select_from(QuizAttempt)
                .join(Lesson, Lesson.id == QuizAttempt.lesson_id)
                .where(QuizAttempt.student_id == student_id, Lesson.course_id == course_id)
            )
        ).scalar_one()
        report.average_score = round(float(lesson_avg), 1) if lesson_avg is not None else None
    else:
        report.average_score = round(float(quiz_avg), 1)

    report.updated_at = datetime.now(timezone.utc)
    return report
