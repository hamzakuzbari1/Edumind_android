"""Parent notifications — real student events, settings-aware, channel-ready."""

from __future__ import annotations

import enum
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationChannel, NotificationType
from app.models.parent_link import ParentStudentLink
from app.models.parent_notification_settings import ParentNotificationSettings
from app.models.profile import StudentProfile
from app.models.user import User
from app.schemas.parent_notifications import PARENT_NOTIFICATION_TYPE_LABELS
from app.services import notification_service

logger = logging.getLogger(__name__)

PARENT_STUDENT_TYPES = {
    NotificationType.parent_student_login.value,
    NotificationType.parent_student_logout.value,
    NotificationType.parent_lesson_completed.value,
    NotificationType.parent_quiz_completed.value,
    NotificationType.parent_low_score.value,
    NotificationType.parent_inactivity.value,
    NotificationType.parent_planner.value,
    NotificationType.parent_alert.value,
}

CATEGORY_TO_TYPE = {
    "login": NotificationType.parent_student_login.value,
    "logout": NotificationType.parent_student_logout.value,
    "lesson": NotificationType.parent_lesson_completed.value,
    "quiz": NotificationType.parent_quiz_completed.value,
    "low_score": NotificationType.parent_low_score.value,
    "inactivity": NotificationType.parent_inactivity.value,
    "planner": NotificationType.parent_planner.value,
}


class ParentNotificationCategory(str, enum.Enum):
    login = "login"
    logout = "logout"
    lesson = "lesson"
    quiz = "quiz"
    low_score = "low_score"
    inactivity = "inactivity"
    planner = "planner"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _student_first_name(student: User | None) -> str:
    if student and student.name:
        return student.name.split()[0]
    return "الطالب"


def _category_from_type(notification_type: str) -> str:
    for cat, ntype in CATEGORY_TO_TYPE.items():
        if ntype == notification_type:
            return cat
    return "general"


def _settings_field(category: ParentNotificationCategory) -> str:
    return {
        ParentNotificationCategory.login: "login_alerts",
        ParentNotificationCategory.logout: "logout_alerts",
        ParentNotificationCategory.lesson: "lesson_alerts",
        ParentNotificationCategory.quiz: "quiz_alerts",
        ParentNotificationCategory.low_score: "low_score_alerts",
        ParentNotificationCategory.inactivity: "inactivity_alerts",
        ParentNotificationCategory.planner: "planner_alerts",
    }[category]


async def _linked_parent_ids(db: AsyncSession, student_id: int) -> list[int]:
    result = await db.execute(
        select(ParentStudentLink.parent_id).where(ParentStudentLink.student_id == student_id)
    )
    return list(result.scalars().all())


async def get_or_create_settings(
    db: AsyncSession, parent_id: int, student_id: int
) -> ParentNotificationSettings:
    result = await db.execute(
        select(ParentNotificationSettings).where(
            ParentNotificationSettings.parent_id == parent_id,
            ParentNotificationSettings.student_id == student_id,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    row = ParentNotificationSettings(parent_id=parent_id, student_id=student_id)
    db.add(row)
    await db.flush()
    return row


def _category_enabled(settings: ParentNotificationSettings, category: ParentNotificationCategory) -> bool:
    return bool(getattr(settings, _settings_field(category), True))


async def _has_dedup_key(db: AsyncSession, parent_id: int, dedup_key: str, *, hours: int = 24) -> bool:
    since = _utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == parent_id,
            Notification.created_at >= since,
            cast(Notification.payload, JSONB)["dedup_key"].astext == dedup_key,
        )
    )
    return int(result.scalar_one() or 0) > 0


async def emit_parent_notification(
    db: AsyncSession,
    *,
    student_id: int,
    category: ParentNotificationCategory,
    title: str,
    body: str,
    payload: dict[str, Any] | None = None,
    dedup_key: str | None = None,
    channel: NotificationChannel = NotificationChannel.in_app,
) -> int:
    """Create in-app notifications for all linked parents respecting per-student settings."""
    parent_ids = await _linked_parent_ids(db, student_id)
    if not parent_ids:
        return 0

    notification_type = CATEGORY_TO_TYPE[category.value]
    base_payload: dict[str, Any] = {
        "student_id": student_id,
        "category": category.value,
        "channel": channel.value,
    }
    if payload:
        base_payload.update(payload)
    if dedup_key:
        base_payload["dedup_key"] = dedup_key

    created = 0
    for parent_id in parent_ids:
        settings = await get_or_create_settings(db, parent_id, student_id)
        if not _category_enabled(settings, category):
            continue
        if dedup_key and await _has_dedup_key(db, parent_id, dedup_key):
            continue
        await notification_service.create_notification(
            db,
            user_id=parent_id,
            notification_type=notification_type,
            title=title[:200],
            body=body,
            payload=base_payload,
            channel=channel,
        )
        created += 1
    return created


async def notify_student_login(db: AsyncSession, student_id: int, *, session_id: int | None = None) -> None:
    student = await db.get(User, student_id)
    name = _student_first_name(student)
    await emit_parent_notification(
        db,
        student_id=student_id,
        category=ParentNotificationCategory.login,
        title=f"{name} دخل المنصة",
        body=f"{name} دخل المنصة",
        payload={"session_id": session_id},
        dedup_key=f"login:{student_id}:{session_id}" if session_id else None,
    )


async def notify_student_logout(
    db: AsyncSession,
    student_id: int,
    *,
    session_id: int | None = None,
    active_minutes: int = 0,
    reason: str | None = None,
) -> None:
    student = await db.get(User, student_id)
    name = _student_first_name(student)
    body = f"{name} غادر المنصة"
    if active_minutes > 0:
        body += f"\nمدة الدراسة:\n{active_minutes} دقيقة"
    await emit_parent_notification(
        db,
        student_id=student_id,
        category=ParentNotificationCategory.logout,
        title=f"{name} غادر المنصة",
        body=body,
        payload={
            "session_id": session_id,
            "active_minutes": active_minutes,
            "logout_reason": reason,
        },
        dedup_key=f"logout:{student_id}:{session_id}" if session_id else None,
    )


async def notify_lesson_completed(
    db: AsyncSession, student_id: int, *, lesson_id: int, lesson_title: str
) -> None:
    student = await db.get(User, student_id)
    name = _student_first_name(student)
    title = f"أكمل {name} درس:"
    body = f"أكمل {name} درس:\n{lesson_title}"
    await emit_parent_notification(
        db,
        student_id=student_id,
        category=ParentNotificationCategory.lesson,
        title=title,
        body=body,
        payload={"lesson_id": lesson_id, "lesson_title": lesson_title},
    )


async def notify_quiz_completed(
    db: AsyncSession,
    student_id: int,
    *,
    subject: str,
    score_percent: int,
    quiz_id: int | None = None,
    lesson_id: int | None = None,
    attempt_id: int | None = None,
) -> None:
    student = await db.get(User, student_id)
    name = _student_first_name(student)
    title = f"أنهى {name} اختبار {subject}"
    body = f"أنهى {name} اختبار {subject}\n\nالنتيجة:\n{score_percent}%"
    await emit_parent_notification(
        db,
        student_id=student_id,
        category=ParentNotificationCategory.quiz,
        title=title,
        body=body,
        payload={
            "subject": subject,
            "score_percent": score_percent,
            "quiz_id": quiz_id,
            "lesson_id": lesson_id,
            "attempt_id": attempt_id,
        },
    )


async def notify_low_score(
    db: AsyncSession,
    student_id: int,
    *,
    subject: str,
    score_percent: int,
    quiz_id: int | None = None,
    lesson_id: int | None = None,
    attempt_id: int | None = None,
) -> None:
    parent_ids = await _linked_parent_ids(db, student_id)
    if not parent_ids:
        return

    student = await db.get(User, student_id)
    name = _student_first_name(student)
    title = f"انخفضت نتيجة {name} في {subject}"
    body = f"انخفضت نتيجة {name} في {subject} إلى {score_percent}%."
    dedup = f"low_score:{student_id}:{lesson_id or quiz_id}:{attempt_id}"

    for parent_id in parent_ids:
        settings = await get_or_create_settings(db, parent_id, student_id)
        if not settings.low_score_alerts:
            continue
        if score_percent >= int(settings.low_score_threshold or 60):
            continue
        if attempt_id and await _has_dedup_key(db, parent_id, dedup):
            continue
        payload: dict[str, Any] = {
            "student_id": student_id,
            "category": ParentNotificationCategory.low_score.value,
            "channel": NotificationChannel.in_app.value,
            "subject": subject,
            "score_percent": score_percent,
            "quiz_id": quiz_id,
            "lesson_id": lesson_id,
            "attempt_id": attempt_id,
        }
        if attempt_id:
            payload["dedup_key"] = dedup
        await notification_service.create_notification(
            db,
            user_id=parent_id,
            notification_type=NotificationType.parent_low_score.value,
            title=title,
            body=body,
            payload=payload,
            channel=NotificationChannel.in_app,
        )


async def _maybe_emit_inactivity(db: AsyncSession, parent_id: int, student_id: int) -> None:
    settings = await get_or_create_settings(db, parent_id, student_id)
    if not settings.inactivity_alerts:
        return

    profile = await db.execute(select(StudentProfile).where(StudentProfile.user_id == student_id))
    prof = profile.scalar_one_or_none()
    if not prof or not prof.last_activity_at:
        return

    last = prof.last_activity_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    inactive_days = (_utcnow() - last).days
    threshold = int(settings.inactivity_days or 3)
    if inactive_days < threshold:
        return

    student = await db.get(User, student_id)
    name = _student_first_name(student)
    day_key = _utcnow().date().isoformat()
    dedup_key = f"inactivity:{student_id}:{day_key}"
    if await _has_dedup_key(db, parent_id, dedup_key):
        return

    await notification_service.create_notification(
        db,
        user_id=parent_id,
        notification_type=NotificationType.parent_inactivity.value,
        title=f"لم يسجل {name} أي نشاط",
        body=f"لم يسجل {name} أي نشاط منذ {inactive_days} أيام.",
        payload={
            "student_id": student_id,
            "category": ParentNotificationCategory.inactivity.value,
            "inactive_days": inactive_days,
            "dedup_key": dedup_key,
            "channel": NotificationChannel.in_app.value,
        },
        channel=NotificationChannel.in_app,
    )


async def _maybe_emit_planner_alert(db: AsyncSession, parent_id: int, student_id: int) -> None:
    settings = await get_or_create_settings(db, parent_id, student_id)
    if not settings.planner_alerts:
        return

    from app.services.parent_planner_visibility_service import build_parent_planner_visibility

    data = await build_parent_planner_visibility(db, student_id)
    overdue_count = int((data.get("commitment") or {}).get("overdue_count") or 0)
    if overdue_count <= 0:
        return

    day_key = _utcnow().date().isoformat()
    dedup_key = f"planner:{student_id}:{day_key}:{overdue_count}"
    if await _has_dedup_key(db, parent_id, dedup_key):
        return

    student = await db.get(User, student_id)
    name = _student_first_name(student)
    await notification_service.create_notification(
        db,
        user_id=parent_id,
        notification_type=NotificationType.parent_planner.value,
        title=f"مهام متأخرة — {name}",
        body=f"لدى {name} {overdue_count} مهام متأخرة.",
        payload={
            "student_id": student_id,
            "category": ParentNotificationCategory.planner.value,
            "overdue_count": overdue_count,
            "dedup_key": dedup_key,
            "channel": NotificationChannel.in_app.value,
        },
        channel=NotificationChannel.in_app,
    )


async def ensure_conditional_alerts(db: AsyncSession, parent_id: int, student_id: int) -> None:
    """Persist inactivity / planner alerts when conditions are met (deduped daily)."""
    await _maybe_emit_inactivity(db, parent_id, student_id)
    await _maybe_emit_planner_alert(db, parent_id, student_id)


def _notification_out(n: Notification) -> dict:
    payload = n.payload or {}
    student_id = payload.get("student_id")
    category = payload.get("category") or _category_from_type(n.type)
    type_label = PARENT_NOTIFICATION_TYPE_LABELS.get(n.type, "تنبيه")
    return {
        "id": n.id,
        "type": n.type,
        "category": category,
        "category_label": type_label,
        "title": n.title,
        "body": n.body,
        "payload": payload,
        "student_id": student_id,
        "is_read": n.is_read,
        "status": "read" if n.is_read else "unread",
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


async def list_parent_notifications(
    db: AsyncSession,
    parent_id: int,
    student_id: int,
    *,
    limit: int = 50,
) -> dict:
    await ensure_conditional_alerts(db, parent_id, student_id)

    q = (
        select(Notification)
        .where(
            Notification.user_id == parent_id,
            Notification.type.in_(PARENT_STUDENT_TYPES),
            cast(Notification.payload, JSONB)["student_id"].astext == str(student_id),
        )
        .order_by(Notification.created_at.desc())
        .limit(min(limit, 100))
    )
    result = await db.execute(q)
    rows = list(result.scalars().all())

    unread_result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == parent_id,
            Notification.type.in_(PARENT_STUDENT_TYPES),
            Notification.is_read.is_(False),
            cast(Notification.payload, JSONB)["student_id"].astext == str(student_id),
        )
    )
    unread = int(unread_result.scalar_one() or 0)
    return {
        "items": [_notification_out(r) for r in rows],
        "unread_count": unread,
    }


async def get_notification_settings(
    db: AsyncSession, parent_id: int, student_id: int
) -> ParentNotificationSettings:
    return await get_or_create_settings(db, parent_id, student_id)


async def update_notification_settings(
    db: AsyncSession,
    parent_id: int,
    student_id: int,
    *,
    login_alerts: bool | None = None,
    logout_alerts: bool | None = None,
    lesson_alerts: bool | None = None,
    quiz_alerts: bool | None = None,
    low_score_alerts: bool | None = None,
    inactivity_alerts: bool | None = None,
    planner_alerts: bool | None = None,
    inactivity_days: int | None = None,
    low_score_threshold: int | None = None,
) -> ParentNotificationSettings:
    row = await get_or_create_settings(db, parent_id, student_id)
    updates = {
        "login_alerts": login_alerts,
        "logout_alerts": logout_alerts,
        "lesson_alerts": lesson_alerts,
        "quiz_alerts": quiz_alerts,
        "low_score_alerts": low_score_alerts,
        "inactivity_alerts": inactivity_alerts,
        "planner_alerts": planner_alerts,
        "inactivity_days": inactivity_days,
        "low_score_threshold": low_score_threshold,
    }
    for field, value in updates.items():
        if value is not None:
            setattr(row, field, value)
    row.updated_at = _utcnow()
    await db.flush()
    return row


async def mark_parent_notification_read(
    db: AsyncSession, parent_id: int, student_id: int, notification_id: int
) -> dict:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == parent_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الإشعار غير موجود")
    payload = row.payload or {}
    sid = payload.get("student_id")
    if sid is not None and int(sid) != int(student_id):
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الإشعار غير موجود")
    if not row.is_read:
        row.is_read = True
        row.read_at = _utcnow()
        await db.flush()
    return _notification_out(row)


def settings_to_dict(row: ParentNotificationSettings) -> dict:
    return {
        "student_id": row.student_id,
        "login_alerts": row.login_alerts,
        "logout_alerts": row.logout_alerts,
        "lesson_alerts": row.lesson_alerts,
        "quiz_alerts": row.quiz_alerts,
        "low_score_alerts": row.low_score_alerts,
        "inactivity_alerts": row.inactivity_alerts,
        "planner_alerts": row.planner_alerts,
        "inactivity_days": row.inactivity_days,
        "low_score_threshold": row.low_score_threshold,
    }
