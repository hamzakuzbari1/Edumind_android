"""Multi-device auth sessions backed by auth_sessions table."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from app.models.auth_session import AuthSession
from app.models.user import User

settings = get_settings()


def _parse_device_type(user_agent: str | None) -> str | None:
    if not user_agent:
        return None
    ua = user_agent.lower()
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "mobile"
    if "tablet" in ua or "ipad" in ua:
        return "tablet"
    return "desktop"


async def create_session(
    db: AsyncSession,
    user: User,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
    device_name: str | None = None,
    viewer_mode: str | None = None,
) -> tuple[AuthSession, str, str]:
    """Returns (session row, access_token, refresh_token plain)."""
    refresh_plain = generate_refresh_token()
    now = datetime.now(timezone.utc)
    session = AuthSession(
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(refresh_plain),
        device_name=device_name or _default_device_name(user_agent),
        device_type=_parse_device_type(user_agent),
        ip_address=ip_address,
        user_agent=user_agent,
        last_seen_at=now,
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    await db.flush()

    from app.services import student_activity_tracking_service

    await student_activity_tracking_service.handle_auth_lifecycle(
        db,
        user.role,
        user.id,
        action="login",
        auth_session_id=session.id,
    )

    token_payload: dict = {"sub": str(user.id), "role": user.role.value}
    if viewer_mode:
        token_payload["viewer_mode"] = viewer_mode
    access = create_access_token(token_payload, session_id=session.id)
    return session, access, refresh_plain


def _invalid_refresh_token() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="رمز تحديث الجلسة غير صالح أو منتهي",
    )


async def rotate_refresh_token(
    db: AsyncSession,
    refresh_token: str,
) -> tuple[AuthSession, User, str, str]:
    """Atomically replace one active session's refresh token and issue a new token pair."""
    token_hash = hash_refresh_token(refresh_token)
    result = await db.execute(
        select(AuthSession)
        .where(AuthSession.refresh_token_hash == token_hash)
        .with_for_update()
    )
    session = result.scalar_one_or_none()
    if not session:
        raise _invalid_refresh_token()

    now = datetime.now(timezone.utc)
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if session.revoked_at is not None or expires_at <= now:
        raise _invalid_refresh_token()

    user = await db.get(User, session.user_id)
    if not user:
        raise _invalid_refresh_token()

    refresh_plain = generate_refresh_token()
    session.refresh_token_hash = hash_refresh_token(refresh_plain)
    session.last_seen_at = now
    session.expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    access = create_access_token(
        {"sub": str(user.id), "role": user.role.value},
        session_id=session.id,
    )
    await db.flush()
    return session, user, access, refresh_plain


def _default_device_name(user_agent: str | None) -> str:
    if not user_agent:
        return "جهاز غير معروف"
    ua = user_agent.lower()
    if "chrome" in ua:
        return "Chrome"
    if "firefox" in ua:
        return "Firefox"
    if "safari" in ua and "chrome" not in ua:
        return "Safari"
    if "edg" in ua:
        return "Edge"
    return "متصفح"


async def get_active_session(db: AsyncSession, session_id: int, user_id: int) -> AuthSession:
    result = await db.execute(
        select(AuthSession).where(
            AuthSession.id == session_id,
            AuthSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="الجلسة غير موجودة")
    now = datetime.now(timezone.utc)
    if session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="تم إلغاء الجلسة")
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        user = await db.get(User, user_id)
        if user:
            from app.services import student_activity_tracking_service

            await student_activity_tracking_service.handle_auth_lifecycle(
                db,
                user.role,
                user_id,
                action="expired",
                auth_session_id=session_id,
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="انتهت صلاحية الجلسة")
    session.last_seen_at = now
    await db.flush()
    return session


async def list_active_sessions(db: AsyncSession, user_id: int) -> list[AuthSession]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(AuthSession)
        .where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .order_by(AuthSession.last_seen_at.desc().nullslast(), AuthSession.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_session(db: AsyncSession, user_id: int, session_id: int) -> None:
    result = await db.execute(
        select(AuthSession).where(AuthSession.id == session_id, AuthSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الجلسة غير موجودة")
    if session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        await db.flush()
        user = await db.get(User, user_id)
        if user:
            from app.services import student_activity_tracking_service

            await student_activity_tracking_service.handle_auth_lifecycle(
                db,
                user.role,
                user_id,
                action="logout",
                auth_session_id=session_id,
            )


async def revoke_all_sessions(
    db: AsyncSession, user_id: int, *, except_session_id: int | None = None
) -> int:
    now = datetime.now(timezone.utc)
    q_filter = select(AuthSession.id).where(
        AuthSession.user_id == user_id,
        AuthSession.revoked_at.is_(None),
    )
    if except_session_id is not None:
        q_filter = q_filter.where(AuthSession.id != except_session_id)
    active = await db.execute(q_filter)
    session_ids = list(active.scalars().all())
    q = (
        update(AuthSession)
        .where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    if except_session_id is not None:
        q = q.where(AuthSession.id != except_session_id)
    result = await db.execute(q)
    user = await db.get(User, user_id)
    if user:
        from app.services import student_activity_tracking_service

        for sid in session_ids:
            await student_activity_tracking_service.handle_auth_lifecycle(
                db,
                user.role,
                user_id,
                action="logout",
                auth_session_id=sid,
            )
    return int(result.rowcount or 0)


async def revoke_by_refresh_token(db: AsyncSession, refresh_token: str) -> None:
    token_hash = hash_refresh_token(refresh_token)
    result = await db.execute(
        select(AuthSession).where(AuthSession.refresh_token_hash == token_hash)
    )
    session = result.scalar_one_or_none()
    if session and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        await db.flush()
        user = await db.get(User, session.user_id)
        if user:
            from app.services import student_activity_tracking_service

            await student_activity_tracking_service.handle_auth_lifecycle(
                db,
                user.role,
                session.user_id,
                action="logout",
                auth_session_id=session.id,
            )
