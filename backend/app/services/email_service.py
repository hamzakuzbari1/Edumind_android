"""Centralized transactional email delivery via Resend."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.email_token import EmailTokenPurpose
from app.models.user import User
from app.services import email_template_service, email_token_service

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailDeliveryError(Exception):
    """Raised when Resend rejects or fails to send."""


def is_email_configured() -> bool:
    return bool(settings.RESEND_API_KEY.strip() and settings.EMAIL_FROM.strip())


def _ensure_configured() -> None:
    if not is_email_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="خدمة البريد غير مهيأة — أضف RESEND_API_KEY و EMAIL_FROM",
        )


async def _send_html(*, to: str, subject: str, html: str) -> dict[str, Any]:
    _ensure_configured()

    try:
        import resend
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="حزمة resend غير مثبتة",
        ) from exc

    resend.api_key = settings.RESEND_API_KEY.strip()
    params: resend.Emails.SendParams = {
        "from": settings.EMAIL_FROM.strip(),
        "to": [to],
        "subject": subject,
        "html": html,
    }

    try:
        response = await resend.Emails.send_async(params)
    except Exception as exc:
        logger.exception("Resend send failed to=%s", to)
        raise EmailDeliveryError(str(exc)) from exc

    if isinstance(response, dict):
        return response
    return {"id": getattr(response, "id", None)}


async def send_welcome_email(user: User) -> dict[str, Any]:
    html = email_template_service.render_welcome_email(
        name=user.name,
        dashboard_url=email_token_service.build_dashboard_url(),
    )
    return await _send_html(
        to=user.email,
        subject="مرحباً بك في EduSpark",
        html=html,
    )


async def send_verification_email(
    db: AsyncSession,
    user: User,
    *,
    expire_hours: int | None = None,
) -> dict[str, Any]:
    hours = expire_hours or settings.EMAIL_VERIFICATION_EXPIRE_HOURS
    raw, _row = await email_token_service.create_email_token(
        db,
        user,
        EmailTokenPurpose.verification,
        expire_hours=hours,
    )
    verify_url = email_token_service.build_verification_url(raw)
    html = email_template_service.render_verify_email(
        name=user.name,
        verify_url=verify_url,
        expires_hours=hours,
    )
    return await _send_html(
        to=user.email,
        subject="تأكيد بريدك الإلكتروني — EduSpark",
        html=html,
    )


async def send_password_reset_email(
    db: AsyncSession,
    user: User,
    *,
    expire_hours: int | None = None,
) -> dict[str, Any]:
    hours = expire_hours or settings.PASSWORD_RESET_EXPIRE_HOURS
    raw, _row = await email_token_service.create_email_token(
        db,
        user,
        EmailTokenPurpose.password_reset,
        expire_hours=hours,
    )
    reset_url = email_token_service.build_password_reset_url(raw)
    html = email_template_service.render_reset_password_email(
        name=user.name,
        reset_url=reset_url,
        expires_hours=hours,
    )
    return await _send_html(
        to=user.email,
        subject="إعادة تعيين كلمة المرور — EduSpark",
        html=html,
    )


async def send_two_factor_code(user: User, code: str, *, context: str = "login") -> dict[str, Any]:
    if not is_email_configured():
        logger.warning("2FA code for %s (email not configured): %s", user.email, code)
        return {"skipped": True, "code": code}
    html = email_template_service.render_two_factor_code_email(
        name=user.name,
        code=code,
        expires_minutes=settings.TWO_FACTOR_CODE_EXPIRE_MINUTES,
    )
    subject = "رمز التحقق — EduSpark"
    if context == "enable":
        subject = "تفعيل المصادقة الثنائية — EduSpark"
    return await _send_html(to=user.email, subject=subject, html=html)


async def send_test_email(to: str) -> dict[str, Any]:
    html = email_template_service.render_test_email(recipient=to)
    return await _send_html(
        to=to,
        subject="اختبار EduSpark Email",
        html=html,
    )
