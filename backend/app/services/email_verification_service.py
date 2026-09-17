"""Email verification — token consume and resend."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_token import EmailTokenPurpose
from app.models.user import User
from app.services import email_service, email_token_service
from app.services.audit_service import log_audit
from app.services.email_service import EmailDeliveryError

logger = logging.getLogger(__name__)


def is_email_verified(user: User) -> bool:
    return user.email_verified_at is not None


async def verify_email_with_token(
    db: AsyncSession,
    token: str,
    *,
    ip_address: str | None = None,
) -> User:
    token_row = await email_token_service.consume_email_token(
        db,
        token,
        EmailTokenPurpose.verification,
    )

    result = await db.execute(select(User).where(User.id == token_row.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="رمز غير صالح")

    user.email_verified_at = datetime.now(timezone.utc)
    await db.flush()

    await log_audit(
        db,
        action="email_verified",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        new_values={"email": user.email},
        ip_address=ip_address,
    )
    return user


async def resend_verification_email(
    db: AsyncSession,
    user: User,
    *,
    ip_address: str | None = None,
) -> dict[str, str]:
    if is_email_verified(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="البريد الإلكتروني مُؤكَّد مسبقاً",
        )

    if not email_service.is_email_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="خدمة البريد غير مهيأة — أضف RESEND_API_KEY و EMAIL_FROM",
        )

    try:
        await email_service.send_verification_email(db, user)
    except EmailDeliveryError as exc:
        logger.exception("Verification email failed for user_id=%s", user.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"تعذر إرسال البريد: {exc}",
        ) from exc

    await log_audit(
        db,
        action="verification_email_resent",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        new_values={"email": user.email},
        ip_address=ip_address,
    )
    return {"ok": True, "detail": "تم إرسال رسالة التأكيد — تحقق من بريدك"}
