"""In-app notifications backed by PostgreSQL."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import PaymentStatus, StudentCourseAccess
from app.services.subscription_access_service import is_access_active
from app.models.notification import Notification, NotificationChannel, NotificationType


async def create_notification(
    db: AsyncSession,
    *,
    user_id: int,
    notification_type: str,
    title: str,
    body: str,
    payload: dict[str, Any] | None = None,
    channel: NotificationChannel = NotificationChannel.in_app,
) -> Notification:
    row = Notification(
        user_id=user_id,
        channel=channel,
        type=notification_type,
        title=title[:200],
        body=body,
        data_json=json.dumps(payload, ensure_ascii=False) if payload else None,
        payload=payload,
        is_read=False,
    )
    db.add(row)
    await db.flush()
    return row


async def notify_course_students(
    db: AsyncSession,
    course_id: int,
    *,
    notification_type: str,
    title: str,
    body: str,
    payload: dict[str, Any] | None = None,
) -> int:
    result = await db.execute(
        select(StudentCourseAccess).where(
            StudentCourseAccess.course_id == course_id,
            StudentCourseAccess.payment_status == PaymentStatus.paid,
        )
    )
    student_ids = [a.student_id for a in result.scalars().all() if is_access_active(a)]
    for sid in student_ids:
        await create_notification(
            db,
            user_id=sid,
            notification_type=notification_type,
            title=title,
            body=body,
            payload=payload,
        )
    return len(student_ids)


async def list_notifications(
    db: AsyncSession,
    user_id: int,
    *,
    limit: int = 50,
    unread_only: bool = False,
) -> list[Notification]:
    q = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        q = q.where(Notification.is_read.is_(False))
    q = q.order_by(Notification.created_at.desc()).limit(min(limit, 100))
    result = await db.execute(q)
    return list(result.scalars().all())


async def unread_count(db: AsyncSession, user_id: int) -> int:
    return int(
        (
            await db.execute(
                select(func.count())
                .select_from(Notification)
                .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            )
        ).scalar_one()
        or 0
    )


async def mark_read(db: AsyncSession, user_id: int, notification_id: int) -> Notification:
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الإشعار غير موجود")
    if not row.is_read:
        row.is_read = True
        row.read_at = datetime.now(timezone.utc)
        await db.flush()
    return row


async def mark_all_read(db: AsyncSession, user_id: int) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True, read_at=now)
    )
    return int(result.rowcount or 0)


def notification_to_dict(n: Notification) -> dict:
    payload = n.payload
    if payload is None and n.data_json:
        try:
            payload = json.loads(n.data_json)
        except Exception:
            payload = None
    return {
        "id": n.id,
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "payload": payload,
        "is_read": n.is_read,
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }
