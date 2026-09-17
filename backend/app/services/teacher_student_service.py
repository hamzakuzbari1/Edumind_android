"""Teacher student search, profiles, analytics, and private notes."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth_session import AuthSession
from app.models.catalog import Course, Subject, TeacherProfile
from app.models.course_quiz import CourseQuiz, CourseQuizAttempt, CourseQuizAttemptStatus
from app.models.enrollment import PaymentStatus, StudentCourseAccess
from app.models.lesson import Lesson
from app.models.parent_link import ParentStudentLink
from app.models.profile import StudentProfile
from app.models.progress import StudentLessonProgress
from app.models.quiz import QuizAttempt
from app.models.teacher_student_note import TeacherStudentNote
from app.models.user import User, UserRole
from app.schemas.teacher_students import (
    TeacherStudentActivityOut,
    TeacherStudentAnalyticsOut,
    TeacherStudentCourseOut,
    TeacherStudentDirectoryRowOut,
    TeacherStudentInfoOut,
    TeacherStudentInsightOut,
    TeacherStudentLearningOut,
    TeacherStudentLinkedParentOut,
    TeacherStudentNoteOut,
    TeacherStudentProfileOut,
    TeacherStudentQuizAnalyticsOut,
    TeacherStudentQuizAttemptOut,
    TeacherStudentSearchOut,
)
from app.services.subscription_access_service import is_access_active, subscription_lifecycle_status
from app.services.teacher_setup_service import get_or_create_teacher_profile
from app.services.planner_intelligence_service import get_planner_visibility_snapshot


async def get_teacher_scoped_planner_visibility(
    db: AsyncSession,
    teacher: User,
    student_id: int,
) -> dict:
    """Planner snapshot filtered to subjects/courses this teacher teaches."""
    await assert_student_in_teacher_scope(db, teacher, student_id)
    tp = await _teacher_profile(db, teacher)
    teacher_course_ids = await _teacher_course_ids(db, tp)
    scoped = await db.execute(
        select(StudentCourseAccess.course_id).where(
            StudentCourseAccess.student_id == student_id,
            StudentCourseAccess.course_id.in_(teacher_course_ids),
            StudentCourseAccess.payment_status == PaymentStatus.paid,
        )
    )
    student_course_ids = list(scoped.scalars().all())
    subject_names = set(await _subject_names_for_courses(db, student_course_ids))

    data = await get_planner_visibility_snapshot(db, student_id)
    if not subject_names:
        return {
            **data,
            "subject_analytics": [],
            "weekly_plan": [],
            "recommendations": [],
            "upcoming": [],
            "completed_tasks": [],
            "missed_tasks": [],
            "summary": "لا توجد مواد مشتركة مع هذا المعلّم",
        }

    def _matches(item: dict) -> bool:
        subj = item.get("subject_name") or item.get("subject") or ""
        course_id = item.get("course_id")
        if course_id is not None and course_id in student_course_ids:
            return True
        return bool(subj and subj in subject_names)

    data["subject_analytics"] = [a for a in data.get("subject_analytics", []) if _matches(a)]
    for key in ("upcoming", "completed_tasks", "missed_tasks", "weekly_plan", "recommendations"):
        data[key] = [t for t in data.get(key, []) if _matches(t)]

    scoped_count = len(data.get("upcoming", [])) + len(data.get("completed_tasks", []))
    if scoped_count == 0:
        data["summary"] = f"لا توجد مهام مخطّطة في موادك ({' · '.join(sorted(subject_names))})"
    else:
        stats = data.get("plan_stats") or {}
        streak = data.get("streak") or {}
        data["summary"] = (
            f"موادك: {' · '.join(sorted(subject_names))} — "
            f"{stats.get('planned_count', 0)} مهام قادمة · "
            f"{stats.get('completed_count', 0)} مكتملة · "
            f"سلسلة {streak.get('current_streak_days', 0)} يوم"
        )
    return data


async def _subject_names_for_courses(db: AsyncSession, course_ids: list[int]) -> list[str]:
    if not course_ids:
        return []
    result = await db.execute(
        select(Subject.name_ar)
        .join(Course, Course.subject_id == Subject.id)
        .where(Course.id.in_(course_ids))
        .distinct()
    )
    return sorted({r[0] for r in result.all() if r[0]})


async def _compute_scoped_study_streak(
    db: AsyncSession,
    *,
    student_id: int,
    course_ids: list[int],
) -> int:
    if not course_ids:
        return 0
    lesson_ids_result = await db.execute(
        select(Lesson.id).where(Lesson.course_id.in_(course_ids), Lesson.is_visible.is_(True))
    )
    lesson_ids = list(lesson_ids_result.scalars().all())
    if not lesson_ids:
        return 0
    rows = await db.execute(
        select(StudentLessonProgress.completed_at).where(
            StudentLessonProgress.student_id == student_id,
            StudentLessonProgress.lesson_id.in_(lesson_ids),
            StudentLessonProgress.completed_at.is_not(None),
        )
    )
    dates = {r[0].date() for r in rows.all() if r[0]}
    if not dates:
        return 0
    today = datetime.now(timezone.utc).date()
    streak = 0
    d = today
    while d in dates:
        streak += 1
        d -= timedelta(days=1)
    if streak == 0:
        d = today - timedelta(days=1)
        while d in dates:
            streak += 1
            d -= timedelta(days=1)
    return streak


async def _build_linked_parents(db: AsyncSession, *, student_id: int) -> list[TeacherStudentLinkedParentOut]:
    result = await db.execute(
        select(ParentStudentLink, User)
        .join(User, User.id == ParentStudentLink.parent_id)
        .where(ParentStudentLink.student_id == student_id)
        .order_by(User.name)
    )
    return [
        TeacherStudentLinkedParentOut(
            parent_id=parent.id,
            full_name=parent.name,
            email=parent.email,
            relationship_label=link.relationship_label,
        )
        for link, parent in result.all()
    ]


def _build_teacher_insights(
    *,
    learning: TeacherStudentLearningOut,
    quiz_analytics: TeacherStudentQuizAnalyticsOut,
    timeline: list[TeacherStudentActivityOut],
    analytics: TeacherStudentAnalyticsOut,
    scope_subjects: list[str],
) -> TeacherStudentInsightOut:
    strengths: list[str] = []
    improvements: list[str] = []
    suggested: list[str] = []

    if analytics.completion_percent >= 70:
        strengths.append("تقدّم جيد في إكمال الدروس")
    elif analytics.completion_percent < 40 and learning.lessons_remaining:
        improvements.append("إكمال الدروس المتبقية")

    if analytics.average_score_percent >= 75 and quiz_analytics.total_completed:
        strengths.append("نتائج قوية في الكويزات")
    elif quiz_analytics.total_completed and analytics.average_score_percent < 60:
        improvements.append("تحسين نتائج الكويزات")

    ai_attempts = [a for a in quiz_analytics.recent_attempts if a.source == "ai"]
    if ai_attempts:
        strengths.append("تفاعل جيد مع المعلّم الذكي")

    if analytics.last_active_date:
        try:
            last_dt = datetime.fromisoformat(analytics.last_active_date.replace("Z", "+00:00"))
            days_ago = (datetime.now(timezone.utc) - last_dt.astimezone(timezone.utc)).days
            if days_ago <= 7:
                strengths.append("حضور منتظم")
            elif days_ago > 14:
                improvements.append("زيادة التفاعل مع المادة")
        except (TypeError, ValueError):
            pass

    if learning.lessons_remaining > learning.lessons_completed and learning.lessons_remaining >= 3:
        improvements.append("الالتزام بالخطة الدراسية")

    if quiz_analytics.total_completed == 0 and learning.lessons_completed:
        improvements.append("حل الكويزات بعد كل درس")

    if not strengths:
        strengths.append("بداية جيدة — استمر في المتابعة")
    if not improvements:
        improvements.append("متابعة الأداء الحالي")

    last_activity = timeline[0] if timeline else None
    last_quiz = quiz_analytics.recent_attempts[0] if quiz_analytics.recent_attempts else None

    if analytics.completion_percent < 50 and learning.lessons_remaining:
        suggested.append("تخصيص جلسة مراجعة للدروس غير المكتملة")
    if quiz_analytics.average_score_percent < 60 and quiz_analytics.total_completed:
        suggested.append("مراجعة أخطاء آخر كويز مع الطالب")
    if not timeline:
        suggested.append("تشجيع الطالب على العودة للمنصة")
    else:
        suggested.append("متابعة التقدّم في الدروس القادمة")

    return TeacherStudentInsightOut(
        strengths=strengths[:4],
        improvements=improvements[:4],
        last_activity_title=last_activity.title if last_activity else None,
        last_activity_at=last_activity.occurred_at if last_activity else None,
        last_quiz_title=last_quiz.quiz_title if last_quiz else None,
        last_quiz_score_percent=last_quiz.score_percent if last_quiz else None,
        last_quiz_at=last_quiz.submitted_at if last_quiz else None,
        suggested_actions=suggested[:4],
        scope_subjects=scope_subjects,
    )

async def _teacher_profile(db: AsyncSession, teacher: User) -> TeacherProfile:
    return await get_or_create_teacher_profile(db, teacher)


async def _teacher_course_ids(
    db: AsyncSession,
    tp: TeacherProfile,
    *,
    grade: int | None = None,
    subject_id: int | None = None,
) -> list[int]:
    q = select(Course.id).where(Course.teacher_profile_id == tp.id, Course.is_active.is_(True))
    if grade is not None:
        q = q.where(Course.grade == grade)
    if subject_id is not None:
        q = q.where(Course.subject_id == subject_id)
    result = await db.execute(q)
    return list(result.scalars().all())


async def _scoped_student_ids(db: AsyncSession, course_ids: list[int]) -> set[int]:
    if not course_ids:
        return set()
    result = await db.execute(
        select(StudentCourseAccess.student_id).where(
            StudentCourseAccess.course_id.in_(course_ids),
            StudentCourseAccess.payment_status == PaymentStatus.paid,
        )
    )
    return set(result.scalars().all())


async def assert_student_in_teacher_scope(db: AsyncSession, teacher: User, student_id: int) -> User:
    tp = await _teacher_profile(db, teacher)
    course_ids = await _teacher_course_ids(db, tp)
    if not course_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الطالب غير موجود")

    in_scope = await db.scalar(
        select(func.count())
        .select_from(StudentCourseAccess)
        .where(
            StudentCourseAccess.student_id == student_id,
            StudentCourseAccess.course_id.in_(course_ids),
            StudentCourseAccess.payment_status == PaymentStatus.paid,
        )
    )
    if not int(in_scope or 0):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الطالب غير موجود")

    student = await db.get(User, student_id)
    if not student or student.role != UserRole.student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الطالب غير موجود")
    return student


async def _last_login_at(db: AsyncSession, student_id: int) -> datetime | None:
    return await db.scalar(
        select(func.max(AuthSession.last_seen_at)).where(
            AuthSession.user_id == student_id,
            AuthSession.revoked_at.is_(None),
        )
    )


async def _compute_student_metrics(
    db: AsyncSession,
    *,
    student_id: int,
    course_ids: list[int],
) -> tuple[int, int, datetime | None, bool]:
    """Returns completion_percent, avg_quiz_percent, last_activity_at, is_active."""
    if not course_ids:
        return 0, 0, None, False

    lessons_result = await db.execute(
        select(Lesson.id, Lesson.course_id).where(
            Lesson.course_id.in_(course_ids),
            Lesson.is_visible.is_(True),
        )
    )
    lesson_rows = lessons_result.all()
    lesson_ids = [r[0] for r in lesson_rows]
    lessons_by_course: dict[int, list[int]] = {}
    for lid, cid in lesson_rows:
        lessons_by_course.setdefault(cid, []).append(lid)

    access_rows = await db.execute(
        select(StudentCourseAccess).where(
            StudentCourseAccess.student_id == student_id,
            StudentCourseAccess.course_id.in_(course_ids),
            StudentCourseAccess.payment_status == PaymentStatus.paid,
        )
    )
    access_list = list(access_rows.scalars().all())
    is_active = any(is_access_active(a) for a in access_list)

    total_lessons = 0
    completed_lessons = 0
    for access in access_list:
        c_lessons = lessons_by_course.get(access.course_id, [])
        total_lessons += len(c_lessons)
        if c_lessons:
            done = int(
                await db.scalar(
                    select(func.count()).select_from(StudentLessonProgress).where(
                        StudentLessonProgress.student_id == student_id,
                        StudentLessonProgress.lesson_id.in_(c_lessons),
                        StudentLessonProgress.completed_at.is_not(None),
                    )
                )
                or 0
            )
            completed_lessons += done

    completion_pct = int(round((completed_lessons / total_lessons) * 100)) if total_lessons else 0

    quiz_percents: list[float] = []
    if lesson_ids:
        ai_attempts = await db.execute(
            select(QuizAttempt.correct_count, QuizAttempt.feedback_json, QuizAttempt.created_at)
            .where(QuizAttempt.student_id == student_id, QuizAttempt.lesson_id.in_(lesson_ids))
        )
        for correct, feedback_json, _ in ai_attempts.all():
            total = 0
            if feedback_json:
                try:
                    total = len(json.loads(feedback_json))
                except Exception:
                    pass
            total = total or max(int(correct or 0), 1)
            quiz_percents.append((int(correct or 0) / total) * 100)

    manual_attempts = await db.execute(
        select(CourseQuizAttempt.percent, CourseQuizAttempt.submitted_at)
        .join(CourseQuiz, CourseQuiz.id == CourseQuizAttempt.quiz_id)
        .where(
            CourseQuizAttempt.student_id == student_id,
            CourseQuiz.course_id.in_(course_ids),
            CourseQuizAttempt.status.in_(
                [CourseQuizAttemptStatus.submitted, CourseQuizAttemptStatus.graded]
            ),
        )
    )
    last_activity: datetime | None = None
    for pct, submitted_at in manual_attempts.all():
        if pct is not None:
            quiz_percents.append(float(pct))
        if submitted_at and (last_activity is None or submitted_at > last_activity):
            last_activity = submitted_at

    if lesson_ids:
        last_progress = await db.scalar(
            select(func.max(StudentLessonProgress.completed_at)).where(
                StudentLessonProgress.student_id == student_id,
                StudentLessonProgress.lesson_id.in_(lesson_ids),
            )
        )
        if last_progress and (last_activity is None or last_progress > last_activity):
            last_activity = last_progress

    avg_quiz = int(round(sum(quiz_percents) / len(quiz_percents))) if quiz_percents else 0
    return completion_pct, avg_quiz, last_activity, is_active


async def search_teacher_students(
    db: AsyncSession,
    teacher: User,
    *,
    q: str | None = None,
    grade: int | None = None,
    subject_id: int | None = None,
) -> TeacherStudentSearchOut:
    tp = await _teacher_profile(db, teacher)
    course_ids = await _teacher_course_ids(db, tp, grade=grade, subject_id=subject_id)
    if not course_ids:
        return TeacherStudentSearchOut()

    query = (
        select(User, StudentProfile, Course, Subject)
        .join(StudentCourseAccess, StudentCourseAccess.student_id == User.id)
        .join(Course, Course.id == StudentCourseAccess.course_id)
        .join(Subject, Subject.id == Course.subject_id)
        .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
        .where(
            User.role == UserRole.student,
            StudentCourseAccess.course_id.in_(course_ids),
            StudentCourseAccess.payment_status == PaymentStatus.paid,
        )
    )

    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.where(or_(User.name.ilike(term), User.email.ilike(term)))

    if grade is not None:
        query = query.where(or_(StudentProfile.grade == grade, Course.grade == grade))

    result = await db.execute(query)
    rows = result.all()

    grouped: dict[int, dict] = {}
    for user, profile, course, subject in rows:
        entry = grouped.setdefault(
            user.id,
            {
                "user": user,
                "profile": profile,
                "subjects": set(),
                "course_ids": set(),
            },
        )
        entry["subjects"].add(subject.name_ar if subject else "—")
        entry["course_ids"].add(course.id)

    directory: list[TeacherStudentDirectoryRowOut] = []
    for sid, data in grouped.items():
        student_course_ids = list(data["course_ids"])
        completion, avg_quiz, last_activity, is_active = await _compute_student_metrics(
            db, student_id=sid, course_ids=student_course_ids
        )
        user = data["user"]
        profile = data["profile"]
        directory.append(
            TeacherStudentDirectoryRowOut(
                student_id=sid,
                full_name=user.name,
                email=user.email,
                grade=profile.grade if profile else None,
                is_active=is_active,
                last_activity_at=last_activity.isoformat() if last_activity else None,
                completion_percent=completion,
                avg_quiz_percent=avg_quiz,
                enrolled_subjects=sorted(data["subjects"]),
            )
        )

    directory.sort(key=lambda r: (r.full_name or "").lower())
    return TeacherStudentSearchOut(students=directory, total=len(directory))


async def _build_learning_overview(
    db: AsyncSession,
    *,
    student_id: int,
    course_ids: list[int],
) -> TeacherStudentLearningOut:
    if not course_ids:
        return TeacherStudentLearningOut()

    courses_result = await db.execute(
        select(Course)
        .where(Course.id.in_(course_ids))
        .options(selectinload(Course.subject))
        .order_by(Course.grade, Course.title)
    )
    courses = list(courses_result.scalars().all())

    access_result = await db.execute(
        select(StudentCourseAccess).where(
            StudentCourseAccess.student_id == student_id,
            StudentCourseAccess.course_id.in_(course_ids),
            StudentCourseAccess.payment_status == PaymentStatus.paid,
        )
    )
    access_by_course = {a.course_id: a for a in access_result.scalars().all()}

    course_rows: list[TeacherStudentCourseOut] = []
    subjects: set[str] = set()
    active_courses = completed_courses = 0
    lessons_completed = lessons_remaining = 0

    for course in courses:
        access = access_by_course.get(course.id)
        if not access:
            continue
        subject_name = course.subject.name_ar if course.subject else "—"
        subjects.add(subject_name)

        lesson_ids_result = await db.execute(
            select(Lesson.id).where(Lesson.course_id == course.id, Lesson.is_visible.is_(True))
        )
        lesson_ids = list(lesson_ids_result.scalars().all())
        total = len(lesson_ids)
        done = 0
        if lesson_ids:
            done = int(
                await db.scalar(
                    select(func.count()).select_from(StudentLessonProgress).where(
                        StudentLessonProgress.student_id == student_id,
                        StudentLessonProgress.lesson_id.in_(lesson_ids),
                        StudentLessonProgress.completed_at.is_not(None),
                    )
                )
                or 0
            )
        progress_pct = int(round((done / total) * 100)) if total else 0
        sub_status = subscription_lifecycle_status(access)
        if is_access_active(access):
            active_courses += 1
        if total and done >= total:
            completed_courses += 1
        lessons_completed += done
        lessons_remaining += max(0, total - done)

        course_rows.append(
            TeacherStudentCourseOut(
                course_id=course.id,
                title=course.title,
                subject_name=subject_name,
                grade=course.grade,
                subscription_status=sub_status,
                progress_percent=progress_pct,
                completed_lessons=done,
                total_lessons=total,
            )
        )

    return TeacherStudentLearningOut(
        enrolled_subjects=sorted(subjects),
        subscriptions=[],
        active_courses=active_courses,
        completed_courses=completed_courses,
        lessons_completed=lessons_completed,
        lessons_remaining=lessons_remaining,
        courses=course_rows,
    )


async def _build_quiz_analytics(
    db: AsyncSession,
    *,
    student_id: int,
    course_ids: list[int],
) -> TeacherStudentQuizAnalyticsOut:
    attempts: list[TeacherStudentQuizAttemptOut] = []
    if not course_ids:
        return TeacherStudentQuizAnalyticsOut()

    manual = await db.execute(
        select(CourseQuizAttempt, CourseQuiz, Course, Subject)
        .join(CourseQuiz, CourseQuiz.id == CourseQuizAttempt.quiz_id)
        .join(Course, Course.id == CourseQuiz.course_id)
        .join(Subject, Subject.id == Course.subject_id)
        .where(
            CourseQuizAttempt.student_id == student_id,
            Course.id.in_(course_ids),
            CourseQuizAttempt.status.in_(
                [CourseQuizAttemptStatus.submitted, CourseQuizAttemptStatus.graded]
            ),
        )
        .order_by(CourseQuizAttempt.submitted_at.desc())
        .limit(20)
    )
    for attempt, quiz, course, subject in manual.all():
        pct = int(round(float(attempt.percent or 0)))
        attempts.append(
            TeacherStudentQuizAttemptOut(
                id=attempt.id,
                quiz_title=quiz.title,
                course_title=course.title,
                subject_name=subject.name_ar if subject else "—",
                score_percent=pct,
                passed=attempt.passed,
                submitted_at=attempt.submitted_at.isoformat() if attempt.submitted_at else None,
                source="manual",
            )
        )

    lesson_ids_result = await db.execute(
        select(Lesson.id, Lesson.title, Lesson.subject, Course.title)
        .join(Course, Course.id == Lesson.course_id)
        .where(Lesson.course_id.in_(course_ids))
    )
    lesson_map = {r[0]: (r[1], r[2], r[3]) for r in lesson_ids_result.all()}
    if lesson_map:
        ai_attempts = await db.execute(
            select(QuizAttempt)
            .where(QuizAttempt.student_id == student_id, QuizAttempt.lesson_id.in_(list(lesson_map.keys())))
            .order_by(QuizAttempt.created_at.desc())
            .limit(10)
        )
        for attempt in ai_attempts.scalars().all():
            title, subject, course_title = lesson_map.get(attempt.lesson_id, ("—", "—", "—"))
            total = max(int(attempt.correct_count or 0), 1)
            if attempt.feedback_json:
                try:
                    total = len(json.loads(attempt.feedback_json)) or total
                except Exception:
                    pass
            pct = int(round((int(attempt.correct_count or 0) / total) * 100))
            attempts.append(
                TeacherStudentQuizAttemptOut(
                    id=attempt.id,
                    quiz_title=f"كويز — {title}",
                    course_title=course_title,
                    subject_name=subject or "—",
                    score_percent=pct,
                    passed=pct >= 60,
                    submitted_at=attempt.created_at.isoformat() if attempt.created_at else None,
                    source="ai",
                )
            )

    attempts.sort(key=lambda a: a.submitted_at or "", reverse=True)
    recent = attempts[:15]
    scores = [a.score_percent for a in recent if a.score_percent is not None]
    return TeacherStudentQuizAnalyticsOut(
        total_completed=len(attempts),
        average_score_percent=int(round(sum(scores) / len(scores))) if scores else 0,
        best_score_percent=max(scores) if scores else 0,
        lowest_score_percent=min(scores) if scores else 0,
        recent_attempts=recent,
    )


async def _build_activity_timeline(
    db: AsyncSession,
    *,
    student_id: int,
    course_ids: list[int],
) -> list[TeacherStudentActivityOut]:
    """Activity limited to courses the teacher owns — no global or language-module events."""
    events: list[TeacherStudentActivityOut] = []
    if not course_ids:
        return events

    lesson_ids_result = await db.execute(
        select(Lesson.id, Lesson.title).where(Lesson.course_id.in_(course_ids), Lesson.is_visible.is_(True))
    )
    lesson_titles = {r[0]: r[1] for r in lesson_ids_result.all()}

    if lesson_titles:
        progress_rows = await db.execute(
            select(StudentLessonProgress)
            .where(
                StudentLessonProgress.student_id == student_id,
                StudentLessonProgress.lesson_id.in_(list(lesson_titles.keys())),
                StudentLessonProgress.completed_at.is_not(None),
            )
            .order_by(StudentLessonProgress.completed_at.desc())
            .limit(12)
        )
        for prog in progress_rows.scalars().all():
            title = lesson_titles.get(prog.lesson_id, "درس")
            events.append(
                TeacherStudentActivityOut(
                    id=f"lesson-{prog.id}",
                    event_type="lesson_viewed",
                    title=f"إكمال درس: {title}",
                    occurred_at=prog.completed_at.isoformat() if prog.completed_at else "",
                )
            )

        ai_attempts = await db.execute(
            select(QuizAttempt, Lesson.title)
            .join(Lesson, Lesson.id == QuizAttempt.lesson_id)
            .where(
                QuizAttempt.student_id == student_id,
                QuizAttempt.lesson_id.in_(list(lesson_titles.keys())),
            )
            .order_by(QuizAttempt.created_at.desc())
            .limit(8)
        )
        for attempt, lesson_title in ai_attempts.all():
            events.append(
                TeacherStudentActivityOut(
                    id=f"ai-quiz-{attempt.id}",
                    event_type="quiz_submitted",
                    title=f"كويز ذكي — {lesson_title}",
                    occurred_at=attempt.created_at.isoformat() if attempt.created_at else "",
                )
            )

    manual = await db.execute(
        select(CourseQuizAttempt, CourseQuiz.title, CourseQuizAttempt.submitted_at)
        .join(CourseQuiz, CourseQuiz.id == CourseQuizAttempt.quiz_id)
        .join(Course, Course.id == CourseQuiz.course_id)
        .where(
            CourseQuizAttempt.student_id == student_id,
            Course.id.in_(course_ids),
            CourseQuizAttempt.status.in_(
                [CourseQuizAttemptStatus.submitted, CourseQuizAttemptStatus.graded]
            ),
        )
        .order_by(CourseQuizAttempt.submitted_at.desc())
        .limit(8)
    )
    for attempt, quiz_title, submitted_at in manual.all():
        events.append(
            TeacherStudentActivityOut(
                id=f"quiz-{attempt.id}",
                event_type="quiz_submitted",
                title=f"كويز — {quiz_title}",
                occurred_at=submitted_at.isoformat() if submitted_at else "",
            )
        )

    events.sort(key=lambda e: e.occurred_at, reverse=True)
    return events[:20]


async def get_teacher_student_profile(
    db: AsyncSession,
    teacher: User,
    student_id: int,
) -> TeacherStudentProfileOut:
    student = await assert_student_in_teacher_scope(db, teacher, student_id)
    tp = await _teacher_profile(db, teacher)
    course_ids = await _teacher_course_ids(db, tp)

    scoped_access = await db.execute(
        select(StudentCourseAccess.course_id).where(
            StudentCourseAccess.student_id == student_id,
            StudentCourseAccess.course_id.in_(course_ids),
            StudentCourseAccess.payment_status == PaymentStatus.paid,
        )
    )
    student_course_ids = list(scoped_access.scalars().all())

    profile = await db.scalar(select(StudentProfile).where(StudentProfile.user_id == student_id))
    last_login = await _last_login_at(db, student_id)
    completion, avg_quiz, last_activity, is_active = await _compute_student_metrics(
        db, student_id=student_id, course_ids=student_course_ids
    )

    account_status = "active" if is_active else "expired"
    learning = await _build_learning_overview(db, student_id=student_id, course_ids=student_course_ids)
    quiz_analytics = await _build_quiz_analytics(db, student_id=student_id, course_ids=student_course_ids)
    timeline = await _build_activity_timeline(db, student_id=student_id, course_ids=student_course_ids)
    scope_subjects = await _subject_names_for_courses(db, student_course_ids)

    streak_val = await _compute_scoped_study_streak(
        db, student_id=student_id, course_ids=student_course_ids
    )
    study_count = learning.lessons_completed + quiz_analytics.total_completed

    notes = await list_teacher_notes(db, teacher, student_id)
    linked_parents = await _build_linked_parents(db, student_id=student_id)
    teacher_insight = _build_teacher_insights(
        learning=learning,
        quiz_analytics=quiz_analytics,
        timeline=timeline,
        analytics=TeacherStudentAnalyticsOut(
            completion_percent=completion,
            average_score_percent=quiz_analytics.average_score_percent or avg_quiz,
            total_study_activity=study_count,
            active_streak=streak_val,
            last_active_date=last_activity.isoformat() if last_activity else None,
        ),
        scope_subjects=scope_subjects,
    )

    scope_label = " · ".join(scope_subjects) if scope_subjects else None

    return TeacherStudentProfileOut(
        info=TeacherStudentInfoOut(
            student_id=student.id,
            full_name=student.name,
            email=student.email,
            grade=profile.grade if profile else None,
            registration_date=student.created_at.isoformat() if student.created_at else None,
            last_login_at=(last_login or last_activity).isoformat() if (last_login or last_activity) else None,
            account_status=account_status,
        ),
        analytics=TeacherStudentAnalyticsOut(
            completion_percent=completion,
            average_score_percent=quiz_analytics.average_score_percent or avg_quiz,
            total_study_activity=study_count,
            active_streak=streak_val,
            last_active_date=last_activity.isoformat() if last_activity else None,
        ),
        learning=learning,
        quiz_analytics=quiz_analytics,
        language=None,
        activity_timeline=timeline,
        notes=notes,
        gamification=None,
        teacher_insight=teacher_insight,
        linked_parents=linked_parents,
        analytics_scope_label=scope_label,
    )


async def list_teacher_notes(
    db: AsyncSession,
    teacher: User,
    student_id: int,
) -> list[TeacherStudentNoteOut]:
    await assert_student_in_teacher_scope(db, teacher, student_id)
    tp = await _teacher_profile(db, teacher)
    result = await db.execute(
        select(TeacherStudentNote)
        .where(
            TeacherStudentNote.teacher_profile_id == tp.id,
            TeacherStudentNote.student_id == student_id,
        )
        .order_by(TeacherStudentNote.updated_at.desc())
    )
    return [
        TeacherStudentNoteOut(
            id=n.id,
            note_text=n.note_text,
            created_at=n.created_at.isoformat() if n.created_at else "",
            updated_at=n.updated_at.isoformat() if n.updated_at else "",
        )
        for n in result.scalars().all()
    ]


async def create_teacher_note(
    db: AsyncSession,
    teacher: User,
    student_id: int,
    note_text: str,
) -> TeacherStudentNoteOut:
    await assert_student_in_teacher_scope(db, teacher, student_id)
    tp = await _teacher_profile(db, teacher)
    note = TeacherStudentNote(
        teacher_profile_id=tp.id,
        student_id=student_id,
        note_text=note_text.strip(),
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return TeacherStudentNoteOut(
        id=note.id,
        note_text=note.note_text,
        created_at=note.created_at.isoformat() if note.created_at else "",
        updated_at=note.updated_at.isoformat() if note.updated_at else "",
    )


async def update_teacher_note(
    db: AsyncSession,
    teacher: User,
    student_id: int,
    note_id: int,
    note_text: str,
) -> TeacherStudentNoteOut:
    await assert_student_in_teacher_scope(db, teacher, student_id)
    tp = await _teacher_profile(db, teacher)
    note = await db.scalar(
        select(TeacherStudentNote).where(
            TeacherStudentNote.id == note_id,
            TeacherStudentNote.teacher_profile_id == tp.id,
            TeacherStudentNote.student_id == student_id,
        )
    )
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملاحظة غير موجودة")
    note.note_text = note_text.strip()
    await db.commit()
    await db.refresh(note)
    return TeacherStudentNoteOut(
        id=note.id,
        note_text=note.note_text,
        created_at=note.created_at.isoformat() if note.created_at else "",
        updated_at=note.updated_at.isoformat() if note.updated_at else "",
    )


async def delete_teacher_note(
    db: AsyncSession,
    teacher: User,
    student_id: int,
    note_id: int,
) -> None:
    await assert_student_in_teacher_scope(db, teacher, student_id)
    tp = await _teacher_profile(db, teacher)
    note = await db.scalar(
        select(TeacherStudentNote).where(
            TeacherStudentNote.id == note_id,
            TeacherStudentNote.teacher_profile_id == tp.id,
            TeacherStudentNote.student_id == student_id,
        )
    )
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملاحظة غير موجودة")
    await db.delete(note)
    await db.commit()
