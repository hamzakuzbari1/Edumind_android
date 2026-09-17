"""Teacher management analytics — real DB only."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analytics import CourseAnalytics, TeacherAnalytics
from app.models.attendance import StudentAttendanceRecord
from app.models.catalog import Course, Subject, TeacherProfile
from app.models.enrollment import PaymentStatus, StudentCourseAccess
from app.models.lesson import Lesson, LessonContentType
from app.models.progress import StudentLessonProgress
from app.models.quiz import QuizAttempt
from app.models.user import User
from app.services.teacher_courses_service import _public_url
from app.services.teacher_setup_service import get_or_create_teacher_profile
from app.schemas.teacher_dashboard import (
    TeacherCourseAnalyticsOut,
    TeacherCourseDetailOut,
    TeacherCourseRowOut,
    TeacherGradesOut,
    TeacherKpiOut,
    TeacherOverviewOut,
    TeacherLessonRowOut,
    TeacherStudentRowOut,
    TeacherSubscriptionSummaryOut,
)
from app.services.subscription_access_service import (
    days_until_expiry,
    is_access_active,
    subscription_lifecycle_status,
    _aware,
)


LESSON_TYPE_LABELS = {
    LessonContentType.video.value: "فيديو",
    LessonContentType.pdf.value: "PDF",
    LessonContentType.homework.value: "واجب",
    LessonContentType.ai.value: "ذكي",
    "composite": "متكامل",
}


async def _teacher_profile(db: AsyncSession, teacher: User) -> TeacherProfile:
    return await get_or_create_teacher_profile(db, teacher)


def _summarize_access_rows(rows: list[StudentCourseAccess]) -> TeacherSubscriptionSummaryOut:
    active = expiring = expired = 0
    for access in rows:
        status = subscription_lifecycle_status(access)
        if status == "active":
            active += 1
        elif status == "expiring_soon":
            expiring += 1
        elif status == "expired":
            expired += 1
    return TeacherSubscriptionSummaryOut(
        active_subscribers=active,
        expiring_soon=expiring,
        expired_subscribers=expired,
    )


async def _paid_access_for_course(db: AsyncSession, course_id: int) -> list[StudentCourseAccess]:
    result = await db.execute(
        select(StudentCourseAccess).where(
            StudentCourseAccess.course_id == course_id,
            StudentCourseAccess.payment_status == PaymentStatus.paid,
        )
    )
    return list(result.scalars().all())


async def _paid_student_ids_for_course(db: AsyncSession, course_id: int) -> list[int]:
    rows = await _paid_access_for_course(db, course_id)
    return [a.student_id for a in rows if is_access_active(a)]


async def _course_lessons(db: AsyncSession, course_id: int) -> list[Lesson]:
    result = await db.execute(
        select(Lesson).where(Lesson.course_id == course_id, Lesson.is_visible.is_(True)).order_by(Lesson.sort_order, Lesson.id)
    )
    return list(result.scalars().all())


def _lesson_type(lesson: Lesson) -> str:
    ct = lesson.content_type
    if ct is None:
        return LessonContentType.video.value if lesson.video_url else LessonContentType.pdf.value
    return ct.value if hasattr(ct, "value") else str(ct)


async def teacher_overview(db: AsyncSession, teacher: User) -> TeacherOverviewOut:
    tp = await _teacher_profile(db, teacher)
    rollup = await db.get(TeacherAnalytics, tp.id)

    courses_result = await db.execute(
        select(Course.id).where(Course.teacher_profile_id == tp.id, Course.is_active.is_(True))
    )
    course_ids = list(courses_result.scalars().all())
    if not course_ids:
        return TeacherOverviewOut(
            kpis=[
                TeacherKpiOut(id="courses", title="المواد", value="0", subtitle="لا توجد مواد بعد", icon="mdi-book-education"),
                TeacherKpiOut(id="students", title="الطلاب المشتركين", value="0", subtitle="—", icon="mdi-account-group"),
                TeacherKpiOut(id="lessons", title="الدروس", value="0", subtitle="—", icon="mdi-play-box-multiple"),
                TeacherKpiOut(id="completion", title="إكمال الدروس", value="0%", subtitle="—", icon="mdi-chart-line"),
            ],
            recent_activity=[],
            subscription_summary=TeacherSubscriptionSummaryOut(),
        )

    if rollup and rollup.updated_at:
        students_count = rollup.total_students
        completion_pct = int(round(float(rollup.average_completion or 0)))
    else:
        students_count = await db.scalar(
            select(func.count(distinct(StudentCourseAccess.student_id))).where(
                StudentCourseAccess.course_id.in_(course_ids),
                StudentCourseAccess.payment_status == PaymentStatus.paid,
            )
        )
        completions = await db.scalar(
            select(func.count())
            .select_from(StudentLessonProgress)
            .join(Lesson, Lesson.id == StudentLessonProgress.lesson_id)
            .where(
                Lesson.course_id.in_(course_ids),
                StudentLessonProgress.completed_at.is_not(None),
            )
        )
        lessons_count_live = await db.scalar(
            select(func.count()).select_from(Lesson).where(
                Lesson.course_id.in_(course_ids), Lesson.is_visible.is_(True)
            )
        )
        denom = (int(students_count or 0) * int(lessons_count_live or 0)) or 0
        completion_pct = int(round((int(completions or 0) / denom) * 100)) if denom else 0

    lessons_count = await db.scalar(
        select(func.count()).select_from(Lesson).where(Lesson.course_id.in_(course_ids), Lesson.is_visible.is_(True))
    )
    if rollup and rollup.updated_at:
        students_display = int(rollup.total_students or 0)
    else:
        students_display = int(students_count or 0)

    kpis = [
        TeacherKpiOut(id="courses", title="المواد", value=str(len(course_ids)), subtitle="مواد/صفوف", icon="mdi-book-education"),
        TeacherKpiOut(id="students", title="الطلاب المشتركين", value=str(students_display), subtitle="مفعّلين", icon="mdi-account-group"),
        TeacherKpiOut(id="lessons", title="الدروس", value=str(int(lessons_count or 0)), subtitle="مرفوعة", icon="mdi-play-box-multiple"),
        TeacherKpiOut(id="completion", title="إكمال الدروس", value=f"{completion_pct}%", subtitle="متوسط عام", icon="mdi-chart-line"),
    ]

    recent_activity: list[str] = []
    # Latest completions or quiz attempts
    recent_progress = await db.execute(
        select(StudentLessonProgress.completed_at)
        .join(Lesson, Lesson.id == StudentLessonProgress.lesson_id)
        .where(
            Lesson.course_id.in_(course_ids),
            StudentLessonProgress.completed_at.is_not(None),
        )
        .order_by(StudentLessonProgress.completed_at.desc())
        .limit(5)
    )
    for dt in recent_progress.scalars().all():
        if isinstance(dt, datetime):
            recent_activity.append(f"تم إكمال درس — {dt.astimezone(timezone.utc).date().isoformat()}")

    access_result = await db.execute(
        select(StudentCourseAccess).where(
            StudentCourseAccess.course_id.in_(course_ids),
            StudentCourseAccess.payment_status == PaymentStatus.paid,
        )
    )
    subscription_summary = _summarize_access_rows(list(access_result.scalars().all()))

    return TeacherOverviewOut(
        kpis=kpis,
        recent_activity=recent_activity,
        subscription_summary=subscription_summary,
    )


async def teacher_grades(db: AsyncSession, teacher: User) -> TeacherGradesOut:
    tp = await _teacher_profile(db, teacher)
    result = await db.execute(
        select(Course)
        .where(Course.teacher_profile_id == tp.id, Course.is_active.is_(True))
        .options(selectinload(Course.subject))
        .order_by(Course.grade.desc(), Course.subject_id)
    )
    courses = list(result.scalars().all())

    rows: list[TeacherCourseRowOut] = []
    for c in courses:
        lesson_count = await db.scalar(select(func.count()).select_from(Lesson).where(Lesson.course_id == c.id, Lesson.is_visible.is_(True)))
        students_count = await db.scalar(
            select(func.count(distinct(StudentCourseAccess.student_id))).where(
                StudentCourseAccess.course_id == c.id,
                StudentCourseAccess.payment_status == PaymentStatus.paid,
            )
        )
        paid_students = int(students_count or 0)
        lessons = int(lesson_count or 0)
        completions = await db.scalar(
            select(func.count()).select_from(StudentLessonProgress).join(Lesson, Lesson.id == StudentLessonProgress.lesson_id).where(
                Lesson.course_id == c.id,
                StudentLessonProgress.completed_at.is_not(None),
            )
        )
        denom = (paid_students * lessons) or 0
        completion_pct = int(round((int(completions or 0) / denom) * 100)) if denom else 0

        rows.append(
            TeacherCourseRowOut(
                course_id=c.id,
                grade=c.grade,
                subject_id=c.subject_id,
                subject_name=c.subject.name_ar if c.subject else "—",
                title=c.title,
                price=c.price,
                thumbnail_url=_public_url(c.thumbnail_url),
                is_published=c.is_published,
                lesson_count=lessons,
                subscribed_students=paid_students,
                completion_percent=completion_pct,
            )
        )
    return TeacherGradesOut(courses=rows)


async def teacher_course_detail(db: AsyncSession, teacher: User, course_id: int) -> TeacherCourseDetailOut:
    tp = await _teacher_profile(db, teacher)
    course_result = await db.execute(
        select(Course)
        .where(Course.id == course_id, Course.teacher_profile_id == tp.id, Course.is_active.is_(True))
        .options(selectinload(Course.subject))
    )
    course = course_result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المادة غير موجودة")

    lessons = await _course_lessons(db, course_id)
    lesson_ids = [l.id for l in lessons]

    paid_access_rows = await _paid_access_for_course(db, course_id)
    sub_summary = _summarize_access_rows(paid_access_rows)
    paid_student_ids = [a.student_id for a in paid_access_rows]
    paid_students = len(paid_student_ids)
    active_student_ids = await _paid_student_ids_for_course(db, course_id)

    # total completions for this course
    completed_count = 0
    if lesson_ids and active_student_ids:
        completed_count = int(
            (
                await db.scalar(
                    select(func.count())
                    .select_from(StudentLessonProgress)
                    .where(
                        StudentLessonProgress.lesson_id.in_(lesson_ids),
                        StudentLessonProgress.student_id.in_(active_student_ids),
                        StudentLessonProgress.completed_at.is_not(None),
                    )
                )
                or 0
            )
        )
    denom = (len(active_student_ids) * len(lesson_ids)) or 0
    completion_pct = int(round((completed_count / denom) * 100)) if denom else 0

    # Lesson completion % per lesson
    lesson_rows: list[TeacherLessonRowOut] = []
    for l in lessons:
        ctype = _lesson_type(l)
        done = 0
        if active_student_ids:
            done = int(
                (
                    await db.scalar(
                        select(func.count(distinct(StudentLessonProgress.student_id))).where(
                            StudentLessonProgress.lesson_id == l.id,
                            StudentLessonProgress.student_id.in_(active_student_ids),
                            StudentLessonProgress.completed_at.is_not(None),
                        )
                    )
                    or 0
                )
            )
        pct = int(round((done / len(active_student_ids)) * 100)) if active_student_ids else 0
        lesson_rows.append(
            TeacherLessonRowOut(
                id=l.id,
                course_id=l.course_id,
                title=l.title,
                content_type=ctype,
                content_type_label=LESSON_TYPE_LABELS.get(ctype, ctype),
                status=l.status.value if l.status else "processed",
                created_at=l.created_at.isoformat() if l.created_at else None,
                completion_percent=pct,
            )
        )

    access_by_student = {a.student_id: a for a in paid_access_rows}

    # Students table (all paid subscriptions: active, expiring, expired)
    student_rows: list[TeacherStudentRowOut] = []
    if paid_student_ids:
        total_lessons = len(lesson_ids)
        for sid in paid_student_ids:
            user = await db.get(User, sid)
            if not user:
                continue

            completed_lessons = 0
            verified_completions = 0
            in_progress_lessons = 0
            if lesson_ids:
                completed_lessons = int(
                    (
                        await db.scalar(
                            select(func.count()).select_from(StudentLessonProgress).where(
                                StudentLessonProgress.student_id == sid,
                                StudentLessonProgress.lesson_id.in_(lesson_ids),
                                StudentLessonProgress.completed_at.is_not(None),
                            )
                        )
                        or 0
                    )
                )
                verified_completions = int(
                    (
                        await db.scalar(
                            select(func.count()).select_from(StudentLessonProgress).where(
                                StudentLessonProgress.student_id == sid,
                                StudentLessonProgress.lesson_id.in_(lesson_ids),
                                StudentLessonProgress.completion_type == "verified",
                            )
                        )
                        or 0
                    )
                )
                in_progress_lessons = int(
                    (
                        await db.scalar(
                            select(func.count()).select_from(StudentLessonProgress).where(
                                StudentLessonProgress.student_id == sid,
                                StudentLessonProgress.lesson_id.in_(lesson_ids),
                                StudentLessonProgress.completed_at.is_(None),
                                StudentLessonProgress.updated_at.is_not(None),
                            )
                        )
                        or 0
                    )
                )
            progress_pct = int(round((completed_lessons / total_lessons) * 100)) if total_lessons else 0

            # last activity: max(progress.completed_at, quiz_attempt.created_at)
            last_completion = await db.scalar(
                select(func.max(StudentLessonProgress.completed_at))
                .select_from(StudentLessonProgress)
                .where(
                    StudentLessonProgress.student_id == sid,
                    StudentLessonProgress.lesson_id.in_(lesson_ids) if lesson_ids else True,
                    StudentLessonProgress.completed_at.is_not(None),
                )
            )
            last_progress = last_completion
            last_quiz = await db.scalar(
                select(func.max(QuizAttempt.created_at))
                .select_from(QuizAttempt)
                .join(Lesson, Lesson.id == QuizAttempt.lesson_id)
                .where(QuizAttempt.student_id == sid, Lesson.course_id == course_id)
            )
            last_activity = max([d for d in [last_progress, last_quiz] if isinstance(d, datetime)], default=None)

            # attendance percent (last 30 days)
            since = datetime.now(timezone.utc) - timedelta(days=30)
            att_total = await db.scalar(
                select(func.count()).select_from(StudentAttendanceRecord).where(
                    StudentAttendanceRecord.student_id == sid, StudentAttendanceRecord.created_at >= since
                )
            )
            att_present = await db.scalar(
                select(func.count()).select_from(StudentAttendanceRecord).where(
                    StudentAttendanceRecord.student_id == sid,
                    StudentAttendanceRecord.created_at >= since,
                    StudentAttendanceRecord.status == "present",
                )
            )
            attendance_pct = int(round((int(att_present or 0) / int(att_total or 0)) * 100)) if att_total else 0

            # quiz percent: avg(correct_count) per attempt (fallback, since we don't store total questions here)
            avg_correct = await db.scalar(
                select(func.avg(QuizAttempt.correct_count))
                .select_from(QuizAttempt)
                .join(Lesson, Lesson.id == QuizAttempt.lesson_id)
                .where(QuizAttempt.student_id == sid, Lesson.course_id == course_id)
            )
            avg_quiz = int(round(float(avg_correct or 0.0) * 10))  # rough scale for display until per-question denominator is added

            access_row = access_by_student.get(sid)
            sub_status = subscription_lifecycle_status(access_row)
            activated = _aware(access_row.activated_at) if access_row else None
            expires = _aware(access_row.expires_at) if access_row else None
            student_rows.append(
                TeacherStudentRowOut(
                    student_id=sid,
                    full_name=user.name,
                    subscription_status=sub_status,
                    activated_at=activated.isoformat() if activated else None,
                    expires_at=expires.isoformat() if expires else None,
                    days_until_expiry=days_until_expiry(access_row) if access_row else None,
                    progress_percent=progress_pct,
                    completed_lessons=completed_lessons,
                    in_progress_lessons=in_progress_lessons,
                    total_lessons=total_lessons,
                    verified_completions=verified_completions,
                    last_completion_at=last_completion.isoformat() if last_completion else None,
                    last_activity_at=last_activity.isoformat() if last_activity else None,
                    attendance_percent=attendance_pct,
                    avg_quiz_percent=avg_quiz,
                )
            )

    analytics = TeacherCourseAnalyticsOut(
        subscribed_students=paid_students,
        active_subscribers=sub_summary.active_subscribers,
        expiring_soon=sub_summary.expiring_soon,
        expired_subscribers=sub_summary.expired_subscribers,
        lesson_count=len(lesson_ids),
        completion_percent=completion_pct,
        avg_quiz_percent=0,
        most_viewed_lesson_title=None,
    )
    return TeacherCourseDetailOut(
        course_id=course.id,
        grade=course.grade,
        subject_id=course.subject_id,
        subject_name=course.subject.name_ar if course.subject else "—",
        title=course.title,
        description=course.description,
        price=course.price,
        thumbnail_url=_public_url(course.thumbnail_url),
        banner_url=_public_url(course.banner_url),
        is_published=course.is_published,
        analytics=analytics,
        lessons=lesson_rows,
        students=sorted(student_rows, key=lambda s: (s.progress_percent, s.full_name), reverse=True),
    )
