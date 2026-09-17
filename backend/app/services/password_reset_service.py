"""Forgot-password request and token-based reset."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.email_token import EmailTokenPurpose
from app.models.user import User
from app.schemas.auth import ResetPasswordRequest
from app.services import auth_session_service, email_service, email_token_service
from app.services.audit_service import log_audit
from app.services.email_service import EmailDeliveryError

logger = logging.getLogger(__name__)

GENERIC_FORGOT_MESSAGE = "إذا كان البريد مسجلاً، ستصلك رسالة لإعادة تعيين كلمة المرور"


async def request_password_reset(
    db: AsyncSession,
    email: str,
    *,
    ip_address: str | None = None,
) -> dict[str, str]:
    normalized = email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized))
    user = result.scalar_one_or_none()

    if not user:
        logger.info("forgot_password_skipped email_not_registered normalized=%s", normalized)
        return {"ok": True, "detail": GENERIC_FORGOT_MESSAGE}

    try:
        await email_service.send_password_reset_email(db, user)
        await log_audit(
            db,
            action="forgot_password_requested",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            ip_address=ip_address,
        )
        logger.info("forgot_password_sent user_id=%s email=%s", user.id, user.email)
    except EmailDeliveryError:
        logger.exception("Password reset email failed for user_id=%s", user.id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            logger.warning("Email not configured — forgot-password for user_id=%s", user.id)
        else:
            raise

    return {"ok": True, "detail": GENERIC_FORGOT_MESSAGE}


async def reset_password_with_token(
    db: AsyncSession,
    body: ResetPasswordRequest,
    *,
    ip_address: str | None = None,
) -> dict[str, str]:
    if body.new_password != body.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="كلمتا المرور الجديدتان غير متطابقتين",
        )

    token_row = await email_token_service.consume_email_token(
        db,
        body.token,
        EmailTokenPurpose.password_reset,
    )

    result = await db.execute(select(User).where(User.id == token_row.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="رمز غير صالح")

    if verify_password(body.new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="كلمة المرور الجديدة يجب أن تختلف عن الحالية",
        )

    user.hashed_password = hash_password(body.new_password)
    await db.flush()

    revoked = await auth_session_service.revoke_all_sessions(db, user.id)

    await log_audit(
        db,
        action="password_reset_completed",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        new_values={"sessions_revoked": revoked},
        ip_address=ip_address,
    )

    return {"ok": True, "detail": "تم تحديث كلمة المرور — يمكنك تسجيل الدخول الآن"}
