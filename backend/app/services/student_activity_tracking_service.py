"""Real study-time tracking — sessions, engagement events, inactivity detection."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import StudentProfile
from app.models.student_activity_tracking import (
    ActivitySessionLogoutReason,
    EngagementEventType,
    StudentActivitySession,
    StudentEngagementEvent,
)
from app.models.user import UserRole
from app.services import attendance_activity_service

logger = logging.getLogger(__name__)

INACTIVITY_THRESHOLD = timedelta(minutes=15)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def _get_profile(db: AsyncSession, student_id: int) -> StudentProfile | None:
    result = await db.execute(select(StudentProfile).where(StudentProfile.user_id == student_id))
    return result.scalar_one_or_none()


async def _touch_last_activity(db: AsyncSession, student_id: int, when: datetime) -> None:
    profile = await _get_profile(db, student_id)
    if profile:
        profile.last_activity_at = when
        await db.flush()


async def _get_open_session(
    db: AsyncSession,
    student_id: int,
    *,
    auth_session_id: int | None = None,
) -> StudentActivitySession | None:
    q = (
        select(StudentActivitySession)
        .where(
            StudentActivitySession.student_id == student_id,
            StudentActivitySession.logout_at.is_(None),
        )
        .order_by(StudentActivitySession.login_at.desc())
        .limit(1)
    )
    if auth_session_id is not None:
        q = q.where(StudentActivitySession.auth_session_id == auth_session_id)
    result = await db.execute(q)
    return result.scalar_one_or_none()


def _compute_counted_seconds(session: StudentActivitySession, now: datetime) -> tuple[int, bool]:
    """Credit active seconds since last activity; detect inactivity gaps."""
    last = _aware(session.last_active_at)
    if last is None:
        return 0, False
    gap = now - last
    if gap > INACTIVITY_THRESHOLD:
        return 0, True
    return max(0, int(gap.total_seconds())), False


def _add_active_seconds(session: StudentActivitySession, seconds: int) -> None:
    if seconds <= 0:
        return
    total_seconds = int(session.active_minutes or 0) * 60 + seconds
    session.active_minutes = total_seconds // 60


async def _append_event(
    db: AsyncSession,
    *,
    student_id: int,
    event_type: EngagementEventType,
    activity_session_id: int | None,
    counted_seconds: int,
    resource_type: str | None = None,
    resource_id: int | None = None,
    path: str | None = None,
    metadata: dict | None = None,
    occurred_at: datetime | None = None,
) -> StudentEngagementEvent:
    when = occurred_at or _utcnow()
    event = StudentEngagementEvent(
        student_id=student_id,
        activity_session_id=activity_session_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        path=path,
        metadata_json=json.dumps(metadata, ensure_ascii=False) if metadata else None,
        counted_seconds=counted_seconds,
        occurred_at=when,
    )
    db.add(event)
    await db.flush()
    return event


async def on_student_login(
    db: AsyncSession,
    student_id: int,
    *,
    auth_session_id: int | None = None,
) -> StudentActivitySession:
    now = _utcnow()
    session = StudentActivitySession(
        student_id=student_id,
        auth_session_id=auth_session_id,
        login_at=now,
        active_minutes=0,
        last_active_at=now,
    )
    db.add(session)
    await db.flush()
    await _append_event(
        db,
        student_id=student_id,
        event_type=EngagementEventType.login,
        activity_session_id=session.id,
        counted_seconds=0,
        metadata={"auth_session_id": auth_session_id},
        occurred_at=now,
    )
    await _touch_last_activity(db, student_id, now)
    try:
        from app.services import parent_notification_service

        await parent_notification_service.notify_student_login(
            db, student_id, session_id=session.id
        )
    except Exception:
        logger.exception("parent login notification failed for student %s", student_id)
    return session


async def close_activity_session(
    db: AsyncSession,
    student_id: int,
    *,
    auth_session_id: int | None = None,
    reason: ActivitySessionLogoutReason,
) -> StudentActivitySession | None:
    session = await _get_open_session(db, student_id, auth_session_id=auth_session_id)
    if not session:
        return None

    now = _utcnow()
    session.logout_at = now
    session.logout_reason = reason

    event_type = {
        ActivitySessionLogoutReason.logout: EngagementEventType.logout,
        ActivitySessionLogoutReason.expired: EngagementEventType.session_expired,
        ActivitySessionLogoutReason.inactivity: EngagementEventType.session_inactive,
    }[reason]

    await _append_event(
        db,
        student_id=student_id,
        event_type=event_type,
        activity_session_id=session.id,
        counted_seconds=0,
        metadata={"reason": reason.value},
        occurred_at=now,
    )
    await db.flush()
    try:
        from app.services import parent_notification_service

        await parent_notification_service.notify_student_logout(
            db,
            student_id,
            session_id=session.id,
            active_minutes=int(session.active_minutes or 0),
            reason=reason.value,
        )
    except Exception:
        logger.exception("parent logout notification failed for student %s", student_id)
    return session


async def close_sessions_for_auth_session(
    db: AsyncSession,
    auth_session_id: int,
    *,
    reason: ActivitySessionLogoutReason,
) -> None:
    result = await db.execute(
        select(StudentActivitySession).where(
            StudentActivitySession.auth_session_id == auth_session_id,
            StudentActivitySession.logout_at.is_(None),
        )
    )
    for session in result.scalars().all():
        await close_activity_session(
            db,
            session.student_id,
            auth_session_id=auth_session_id,
            reason=reason,
        )


async def record_engagement_event(
    db: AsyncSession,
    student_id: int,
    event_type: EngagementEventType,
    *,
    auth_session_id: int | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    path: str | None = None,
    metadata: dict | None = None,
) -> StudentEngagementEvent:
    """Record platform activity and credit real study seconds (excludes idle gaps > 15 min)."""
    now = _utcnow()
    session = await _get_open_session(db, student_id, auth_session_id=auth_session_id)
    counted_seconds = 0
    inactive_detected = False

    if session:
        counted_seconds, inactive_detected = _compute_counted_seconds(session, now)
        if inactive_detected:
            await _append_event(
                db,
                student_id=student_id,
                event_type=EngagementEventType.session_inactive,
                activity_session_id=session.id,
                counted_seconds=0,
                metadata={"gap_minutes": 15},
                occurred_at=now,
            )
        if counted_seconds > 0:
            _add_active_seconds(session, counted_seconds)
            await attendance_activity_service.record_study_seconds(
                db,
                student_id,
                counted_seconds,
                source=event_type.value,
            )
        session.last_active_at = now
    else:
        session = await on_student_login(db, student_id, auth_session_id=auth_session_id)

    event = await _append_event(
        db,
        student_id=student_id,
        event_type=event_type,
        activity_session_id=session.id if session else None,
        counted_seconds=counted_seconds,
        resource_type=resource_type,
        resource_id=resource_id,
        path=path,
        metadata=metadata,
        occurred_at=now,
    )
    await _touch_last_activity(db, student_id, now)
    return event


async def maybe_close_inactive_sessions(db: AsyncSession, student_id: int) -> None:
    """Close open sessions when last real activity exceeded the inactivity threshold."""
    session = await _get_open_session(db, student_id)
    if not session or not session.last_active_at:
        return
    last = _aware(session.last_active_at)
    if last and _utcnow() - last > INACTIVITY_THRESHOLD:
        await close_activity_session(
            db,
            student_id,
            auth_session_id=session.auth_session_id,
            reason=ActivitySessionLogoutReason.inactivity,
        )


async def get_student_activity_summary(db: AsyncSession, student_id: int) -> dict:
    profile = await _get_profile(db, student_id)
    open_session = await _get_open_session(db, student_id)
    today = _utcnow().date()
    today_start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)

    today_seconds = int(
        (
            await db.execute(
                select(func.coalesce(func.sum(StudentEngagementEvent.counted_seconds), 0)).where(
                    StudentEngagementEvent.student_id == student_id,
                    StudentEngagementEvent.occurred_at >= today_start,
                )
            )
        ).scalar_one()
        or 0
    )

    week_start = today_start - timedelta(days=today.weekday())
    week_seconds = int(
        (
            await db.execute(
                select(func.coalesce(func.sum(StudentEngagementEvent.counted_seconds), 0)).where(
                    StudentEngagementEvent.student_id == student_id,
                    StudentEngagementEvent.occurred_at >= week_start,
                )
            )
        ).scalar_one()
        or 0
    )

    return {
        "last_activity_at": profile.last_activity_at.isoformat() if profile and profile.last_activity_at else None,
        "active_session_id": open_session.id if open_session else None,
        "session_login_at": open_session.login_at.isoformat() if open_session else None,
        "session_active_minutes": int(open_session.active_minutes or 0) if open_session else 0,
        "today_active_minutes": today_seconds // 60,
        "week_active_minutes": week_seconds // 60,
        "inactivity_threshold_minutes": 15,
    }


async def list_activity_sessions(
    db: AsyncSession,
    student_id: int,
    *,
    limit: int = 30,
    since: date | None = None,
) -> list[dict]:
    q = (
        select(StudentActivitySession)
        .where(StudentActivitySession.student_id == student_id)
        .order_by(StudentActivitySession.login_at.desc())
        .limit(limit)
    )
    if since:
        since_dt = datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc)
        q = q.where(StudentActivitySession.login_at >= since_dt)

    result = await db.execute(q)
    rows: list[dict] = []
    for row in result.scalars().all():
        rows.append(
            {
                "id": row.id,
                "login_at": row.login_at.isoformat() if row.login_at else None,
                "logout_at": row.logout_at.isoformat() if row.logout_at else None,
                "logout_reason": row.logout_reason.value if row.logout_reason else None,
                "active_minutes": int(row.active_minutes or 0),
                "auth_session_id": row.auth_session_id,
            }
        )
    return rows


async def list_engagement_events(
    db: AsyncSession,
    student_id: int,
    *,
    limit: int = 50,
    event_type: EngagementEventType | None = None,
) -> list[dict]:
    q = (
        select(StudentEngagementEvent)
        .where(StudentEngagementEvent.student_id == student_id)
        .order_by(StudentEngagementEvent.occurred_at.desc())
        .limit(limit)
    )
    if event_type:
        q = q.where(StudentEngagementEvent.event_type == event_type)

    result = await db.execute(q)
    out: list[dict] = []
    for row in result.scalars().all():
        out.append(
            {
                "id": row.id,
                "event_type": row.event_type.value,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "path": row.path,
                "counted_seconds": int(row.counted_seconds or 0),
                "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
            }
        )
    return out


async def handle_auth_lifecycle(
    db: AsyncSession,
    user_role: UserRole,
    user_id: int,
    *,
    action: str,
    auth_session_id: int | None = None,
) -> None:
    if user_role != UserRole.student:
        return
    if action == "login":
        await on_student_login(db, user_id, auth_session_id=auth_session_id)
    elif action == "logout" and auth_session_id:
        await close_sessions_for_auth_session(
            db, auth_session_id, reason=ActivitySessionLogoutReason.logout
        )
    elif action == "expired" and auth_session_id:
        await close_sessions_for_auth_session(
            db, auth_session_id, reason=ActivitySessionLogoutReason.expired
        )
