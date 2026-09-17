"""Post-commit side effects: attendance, notifications, analytics rollups, gamification."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Course
from app.models.lesson import Lesson
from app.models.notification import NotificationType
from app.models.parent_link import ParentStudentLink
from app.models.user import UserRole
from app.services import (
    analytics_rollup_service,
    grade_report_service,
    notification_service,
)

logger = logging.getLogger(__name__)


async def _apply_study_streak_xp(db: AsyncSession, student_id: int) -> None:
    from app.services.gamification import xp_service
    from app.services.planner_streak_service import record_study_activity

    streak, new_study_day = await record_study_activity(db, student_id)
    await xp_service.on_study_streak_updated(db, student_id, streak, new_study_day=new_study_day)


async def after_lesson_completed(db: AsyncSession, student_id: int, lesson_id: int) -> None:
    from app.models.student_activity_tracking import EngagementEventType
    from app.services import student_activity_tracking_service

    await student_activity_tracking_service.record_engagement_event(
        db,
        student_id,
        EngagementEventType.lesson_completed,
        resource_type="lesson",
        resource_id=lesson_id,
    )
    lesson = await db.get(Lesson, lesson_id)
    if lesson and lesson.course_id:
        await grade_report_service.refresh_student_grade_reports(db, student_id)
        await analytics_rollup_service.refresh_course_analytics(db, lesson.course_id)
        await analytics_rollup_service.refresh_student_analytics(db, student_id)
        course = await db.get(Course, lesson.course_id)
        if course:
            await analytics_rollup_service.refresh_teacher_analytics(db, course.teacher_profile_id)

    from app.services.gamification import xp_service

    await xp_service.on_lesson_completed(db, student_id, lesson_id)
    await _apply_study_streak_xp(db, student_id)

    from app.models.user import User
    from app.services.activity_service import log_lesson_completed

    student = await db.get(User, student_id)
    if student and lesson:
        child_name = student.name.split()[0] if student.name else "الطالب"
        await log_lesson_completed(
            db,
            student_id=student_id,
            student_name=child_name,
            lesson_title=lesson.title,
            subject=lesson.subject or "الدرس",
            lesson_id=lesson_id,
        )
        from app.services import parent_notification_service

        await parent_notification_service.notify_lesson_completed(
            db,
            student_id,
            lesson_id=lesson_id,
            lesson_title=lesson.title,
        )

    from app.services import student_learning_profile_service

    await student_learning_profile_service.record_lesson_completion(db, student_id, lesson_id)


async def after_lesson_quiz_submitted(
    db: AsyncSession, student_id: int, lesson_id: int, score_percent: int, attempt_id: int
) -> None:
    from app.models.student_activity_tracking import EngagementEventType
    from app.services import student_activity_tracking_service

    await student_activity_tracking_service.record_engagement_event(
        db,
        student_id,
        EngagementEventType.quiz_submitted,
        resource_type="lesson_quiz",
        resource_id=lesson_id,
        metadata={"attempt_id": attempt_id, "score_percent": score_percent},
    )
    from app.services.gamification import xp_service

    await xp_service.on_lesson_quiz_submitted(db, student_id, lesson_id, score_percent, attempt_id)
    await _apply_study_streak_xp(db, student_id)

    lesson = await db.get(Lesson, lesson_id)
    subject = (lesson.subject or lesson.title or "الاختبار") if lesson else "الاختبار"
    from app.services import parent_notification_service

    await parent_notification_service.notify_quiz_completed(
        db,
        student_id,
        subject=subject,
        score_percent=score_percent,
        lesson_id=lesson_id,
        attempt_id=attempt_id,
    )
    await parent_notification_service.notify_low_score(
        db,
        student_id,
        subject=subject,
        score_percent=score_percent,
        lesson_id=lesson_id,
        attempt_id=attempt_id,
    )


async def after_quiz_submitted(
    db: AsyncSession, student_id: int, quiz_id: int, course_id: int, *, attempt_id: int, score_percent: int
) -> None:
    from app.models.student_activity_tracking import EngagementEventType
    from app.services import student_activity_tracking_service

    await student_activity_tracking_service.record_engagement_event(
        db,
        student_id,
        EngagementEventType.quiz_submitted,
        resource_type="course_quiz",
        resource_id=quiz_id,
        metadata={"attempt_id": attempt_id, "score_percent": score_percent, "course_id": course_id},
    )
    await grade_report_service.refresh_student_grade_reports(db, student_id)
    await analytics_rollup_service.refresh_course_analytics(db, course_id)
    await analytics_rollup_service.refresh_student_analytics(db, student_id)
    course = await db.get(Course, course_id)
    if course:
        await analytics_rollup_service.refresh_teacher_analytics(db, course.teacher_profile_id)

    from app.services.gamification import xp_service

    await xp_service.on_manual_quiz_submitted(db, student_id, attempt_id, score_percent)
    await _apply_study_streak_xp(db, student_id)

    subject = course.title if course else "الاختبار"
    from app.services import parent_notification_service

    await parent_notification_service.notify_quiz_completed(
        db,
        student_id,
        subject=subject,
        score_percent=score_percent,
        quiz_id=quiz_id,
        attempt_id=attempt_id,
    )
    await parent_notification_service.notify_low_score(
        db,
        student_id,
        subject=subject,
        score_percent=score_percent,
        quiz_id=quiz_id,
        attempt_id=attempt_id,
    )


async def after_planner_task_completed(db: AsyncSession, student_id: int, slot_id: int) -> None:
    from app.models.student_activity_tracking import EngagementEventType
    from app.services import student_activity_tracking_service

    await student_activity_tracking_service.record_engagement_event(
        db,
        student_id,
        EngagementEventType.planner_activity,
        resource_type="planner_slot",
        resource_id=slot_id,
    )
    from app.services.gamification import xp_service

    await xp_service.on_planner_task_completed(db, student_id, slot_id)
    await _apply_study_streak_xp(db, student_id)


async def after_payment_success(db: AsyncSession, student_id: int, course_id: int) -> None:
    await grade_report_service.refresh_student_grade_reports(db, student_id)
    await analytics_rollup_service.refresh_course_analytics(db, course_id)
    await analytics_rollup_service.refresh_student_analytics(db, student_id)
    course = await db.get(Course, course_id)
    if course:
        await analytics_rollup_service.refresh_teacher_analytics(db, course.teacher_profile_id)


async def after_course_published(db: AsyncSession, course_id: int) -> None:
    await analytics_rollup_service.refresh_course_analytics(db, course_id)
    course = await db.get(Course, course_id)
    if course:
        await analytics_rollup_service.refresh_teacher_analytics(db, course.teacher_profile_id)


async def notify_lesson_published(
    db: AsyncSession, *, course_id: int, lesson_title: str, lesson_id: int
) -> None:
    await notification_service.notify_course_students(
        db,
        course_id,
        notification_type=NotificationType.lesson_published.value,
        title="درس جديد",
        body=f"تم نشر درس: {lesson_title}",
        payload={"lesson_id": lesson_id, "course_id": course_id},
    )


async def notify_quiz_published(
    db: AsyncSession, *, course_id: int, quiz_title: str, quiz_id: int
) -> None:
    await notification_service.notify_course_students(
        db,
        course_id,
        notification_type=NotificationType.quiz_published.value,
        title="اختبار جديد",
        body=f"اختبار متاح: {quiz_title}",
        payload={"quiz_id": quiz_id, "course_id": course_id},
    )


async def notify_payment_received(
    db: AsyncSession, *, student_id: int, course_title: str, amount: float | None = None
) -> None:
    body = f"تم تفعيل الاشتراك في {course_title}"
    if amount is not None:
        body += f" — {amount}"
    await notification_service.create_notification(
        db,
        user_id=student_id,
        notification_type=NotificationType.payment_received.value,
        title="تم استلام الدفع",
        body=body,
        payload={"course_title": course_title, "amount": amount},
    )


async def notify_subscription_expiring(
    db: AsyncSession, *, student_id: int, course_title: str, days_left: int
) -> None:
    await notification_service.create_notification(
        db,
        user_id=student_id,
        notification_type=NotificationType.subscription_expiring.value,
        title="اشتراك على وشك الانتهاء",
        body=f"اشتراك {course_title} ينتهي خلال {days_left} يوم",
        payload={"course_title": course_title, "days_left": days_left},
    )


async def notify_homework_graded(
    db: AsyncSession, *, student_id: int, title: str, score: int | None = None
) -> None:
    body = f"تم تقييم الواجب: {title}"
    if score is not None:
        body += f" — {score}%"
    await notification_service.create_notification(
        db,
        user_id=student_id,
        notification_type=NotificationType.homework_graded.value,
        title="تم تقييم الواجب",
        body=body,
        payload={"title": title, "score": score},
    )


async def notify_parent_alert(
    db: AsyncSession, *, student_id: int, title: str, body: str, payload: dict | None = None
) -> None:
    result = await db.execute(
        select(ParentStudentLink.parent_id).where(ParentStudentLink.student_id == student_id)
    )
    parent_ids = list(result.scalars().all())
    for pid in parent_ids:
        await notification_service.create_notification(
            db,
            user_id=pid,
            notification_type=NotificationType.parent_alert.value,
            title=title,
            body=body,
            payload={**(payload or {}), "student_id": student_id, "category": "general", "channel": "in_app"},
        )
