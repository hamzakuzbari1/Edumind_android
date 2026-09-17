"""Scheduled checks: expiry warnings and expired subscription notifications."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.enrollment import PaymentStatus, StudentCourseAccess
from app.models.notification import Notification, NotificationType
from app.services import notification_service
from app.services.integration_hooks import notify_parent_alert
from app.services.subscription_access_service import _aware

logger = logging.getLogger(__name__)
settings = get_settings()

EXPIRY_ALERT_DAYS = (7, 3, 1)


async def _notification_exists(
    db: AsyncSession,
    *,
    user_id: int,
    notification_type: str,
    access_id: int,
    marker: str,
) -> bool:
    result = await db.execute(
        select(Notification.id)
        .where(
            Notification.user_id == user_id,
            Notification.type == notification_type,
            Notification.payload.contains({"access_id": access_id, "marker": marker}),
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _send_student_notification(
    db: AsyncSession,
    *,
    access: StudentCourseAccess,
    course_title: str,
    notification_type: str,
    title: str,
    body: str,
    marker: str,
    extra_payload: dict | None = None,
) -> bool:
    if await _notification_exists(
        db,
        user_id=access.student_id,
        notification_type=notification_type,
        access_id=access.id,
        marker=marker,
    ):
        return False
    payload = {
        "access_id": access.id,
        "course_id": access.course_id,
        "course_title": course_title,
        "marker": marker,
        **(extra_payload or {}),
    }
    await notification_service.create_notification(
        db,
        user_id=access.student_id,
        notification_type=notification_type,
        title=title,
        body=body,
        payload=payload,
    )
    return True


async def _notify_parents_subscription(
    db: AsyncSession,
    *,
    student_id: int,
    title: str,
    body: str,
    payload: dict,
) -> None:
    await notify_parent_alert(db, student_id=student_id, title=title, body=body, payload=payload)


async def run_expiration_check(db: AsyncSession) -> dict[str, int]:
    """Scan paid subscriptions; send 7/3/1-day warnings and expired notices."""
    now = datetime.now(timezone.utc)
    stats = {"warnings": 0, "expired": 0, "scanned": 0}

    result = await db.execute(
        select(StudentCourseAccess)
        .where(StudentCourseAccess.payment_status == PaymentStatus.paid)
        .options(selectinload(StudentCourseAccess.course))
    )
    rows = list(result.scalars().all())
    stats["scanned"] = len(rows)

    for access in rows:
        course = access.course
        course_title = course.title if course else "المادة"
        expires = _aware(access.expires_at)
        if expires is None:
            continue

        if expires <= now:
            marker = "expired"
            sent = await _send_student_notification(
                db,
                access=access,
                course_title=course_title,
                notification_type=NotificationType.subscription_expired.value,
                title="انتهى الاشتراك",
                body=f"انتهى اشتراكك في {course_title}. جدّد الاشتراك لاستعادة الوصول.",
                marker=marker,
            )
            if sent:
                stats["expired"] += 1
                await _notify_parents_subscription(
                    db,
                    student_id=access.student_id,
                    title="انتهى اشتراك الطالب",
                    body=f"انتهى اشتراك {course_title} — يمكن التجديد من صفحة الاشتراكات.",
                    payload={"course_id": access.course_id, "access_id": access.id, "marker": marker},
                )
            continue

        days_left = (expires.date() - now.date()).days
        if days_left not in EXPIRY_ALERT_DAYS:
            continue

        marker = f"expiring_d{days_left}"
        sent = await _send_student_notification(
            db,
            access=access,
            course_title=course_title,
            notification_type=NotificationType.subscription_expiring.value,
            title="اشتراك على وشك الانتهاء",
            body=f"اشتراك {course_title} ينتهي خلال {days_left} يوم",
            marker=marker,
            extra_payload={"days_left": days_left},
        )
        if sent:
            stats["warnings"] += 1
            await _notify_parents_subscription(
                db,
                student_id=access.student_id,
                title="تنبيه اشتراك",
                body=f"اشتراك {course_title} ينتهي خلال {days_left} يوم",
                payload={
                    "course_id": access.course_id,
                    "access_id": access.id,
                    "days_left": days_left,
                    "marker": marker,
                },
            )

    return stats
