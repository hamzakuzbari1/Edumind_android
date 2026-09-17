"""Secure single-use email tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_refresh_token, hash_refresh_token
from app.models.email_token import EmailToken, EmailTokenPurpose
from app.models.user import User


def _hash_token(raw_token: str) -> str:
    return hash_refresh_token(raw_token)


def _generate_raw_token() -> str:
    return generate_refresh_token()


def _frontend_base_url() -> str:
    from app.core.config import get_settings

    settings = get_settings()
    origins = [o.strip() for o in (settings.CORS_ORIGINS or "").split(",") if o.strip()]
    return (origins[0] if origins else "http://localhost:5173").rstrip("/")


async def create_email_token(
    db: AsyncSession,
    user: User,
    purpose: EmailTokenPurpose,
    *,
    expire_hours: int,
) -> tuple[str, EmailToken]:
    """Create a fresh token; invalidates previous unused tokens for the same purpose."""
    now = datetime.now(timezone.utc)

    await db.execute(
        update(EmailToken)
        .where(
            EmailToken.user_id == user.id,
            EmailToken.purpose == purpose,
            EmailToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    raw = _generate_raw_token()
    row = EmailToken(
        user_id=user.id,
        token_hash=_hash_token(raw),
        purpose=purpose,
        expires_at=now + timedelta(hours=expire_hours),
    )
    db.add(row)
    await db.flush()
    return raw, row


async def consume_email_token(
    db: AsyncSession,
    raw_token: str,
    purpose: EmailTokenPurpose,
) -> EmailToken:
    """Validate and mark a token as used (single-use)."""
    token_hash = _hash_token(raw_token.strip())
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(EmailToken).where(
            EmailToken.token_hash == token_hash,
            EmailToken.purpose == purpose,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="رمز غير صالح أو منتهي")
    if row.used_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="تم استخدام هذا الرمز مسبقاً")
    if row.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="انتهت صلاحية الرمز")

    row.used_at = now
    await db.flush()
    return row


def build_verification_url(raw_token: str) -> str:
    return f"{_frontend_base_url()}/verify-email?token={raw_token}"


def build_password_reset_url(raw_token: str) -> str:
    return f"{_frontend_base_url()}/reset-password?token={raw_token}"


def build_dashboard_url() -> str:
    return f"{_frontend_base_url()}/login"
