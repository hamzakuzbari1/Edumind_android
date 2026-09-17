"""Two-factor authentication — email OTP now, TOTP-ready provider layer."""

from __future__ import annotations

import logging
import secrets
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import generate_refresh_token, hash_refresh_token, verify_password
from app.models.two_factor import TwoFactorChallenge, TwoFactorMethod, TwoFactorPurpose
from app.models.user import User
from app.services.audit_service import log_audit
from app.services.email_service import EmailDeliveryError, is_email_configured

logger = logging.getLogger(__name__)
settings = get_settings()


def _hash_value(raw: str) -> str:
    return hash_refresh_token(raw.strip())


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return email
    visible = local[:1] if local else "*"
    return f"{visible}***@{domain}"


class TwoFactorProvider(ABC):
    """Pluggable 2FA delivery — email today, authenticator apps later."""

    @abstractmethod
    async def deliver_code(self, db: AsyncSession, user: User, code: str, *, context: str) -> None:
        ...


class EmailTwoFactorProvider(TwoFactorProvider):
    async def deliver_code(self, db: AsyncSession, user: User, code: str, *, context: str) -> None:
        from app.services import email_service

        await email_service.send_two_factor_code(user, code, context=context)


class TotpTwoFactorProvider(TwoFactorProvider):
    async def deliver_code(self, db: AsyncSession, user: User, code: str, *, context: str) -> None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="تطبيق المصادقة غير مفعّل بعد — استخدم البريد الإلكتروني",
        )


def get_two_factor_provider(method: str | None) -> TwoFactorProvider:
    if method == TwoFactorMethod.totp.value:
        return TotpTwoFactorProvider()
    return EmailTwoFactorProvider()


def is_two_factor_enabled(user: User) -> bool:
    return bool(user.two_factor_enabled)


def _expire_minutes() -> int:
    return max(1, int(settings.TWO_FACTOR_CODE_EXPIRE_MINUTES))


async def _invalidate_open_challenges(
    db: AsyncSession,
    user_id: int,
    purpose: TwoFactorPurpose,
) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(
        update(TwoFactorChallenge)
        .where(
            TwoFactorChallenge.user_id == user_id,
            TwoFactorChallenge.purpose == purpose.value,
            TwoFactorChallenge.used_at.is_(None),
        )
        .values(used_at=now)
    )


async def _create_challenge(
    db: AsyncSession,
    user: User,
    purpose: TwoFactorPurpose,
    *,
    ip_address: str | None = None,
    device_name: str | None = None,
) -> tuple[str, str, TwoFactorChallenge]:
    """Returns (challenge_token, plain_code, row)."""
    now = datetime.now(timezone.utc)
    await _invalidate_open_challenges(db, user.id, purpose)

    code = _generate_code()
    challenge_token = generate_refresh_token()
    row = TwoFactorChallenge(
        user_id=user.id,
        purpose=purpose.value,
        challenge_token_hash=_hash_value(challenge_token),
        code_hash=_hash_value(code),
        expires_at=now + timedelta(minutes=_expire_minutes()),
        last_sent_at=now,
        ip_address=ip_address,
        device_name=device_name,
    )
    db.add(row)
    await db.flush()
    return challenge_token, code, row


async def _get_active_challenge(
    db: AsyncSession,
    challenge_token: str,
    purpose: TwoFactorPurpose,
) -> TwoFactorChallenge:
    now = datetime.now(timezone.utc)
    token_hash = _hash_value(challenge_token)
    row = await db.scalar(
        select(TwoFactorChallenge).where(
            TwoFactorChallenge.challenge_token_hash == token_hash,
            TwoFactorChallenge.purpose == purpose.value,
        )
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="جلسة التحقق غير صالحة")
    if row.used_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="تم استخدام رمز التحقق مسبقاً")
    if row.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="انتهت صلاحية رمز التحقق — اطلب رمزاً جديداً")
    if row.failed_attempts >= settings.TWO_FACTOR_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="تجاوزت عدد المحاولات — اطلب رمزاً جديداً",
        )
    return row


async def _verify_code_on_challenge(
    db: AsyncSession,
    challenge: TwoFactorChallenge,
    code: str,
) -> None:
    stored = challenge.code_hash
    submitted = _hash_value(code.strip())
    if submitted != stored:
        challenge.failed_attempts += 1
        await db.flush()
        remaining = max(0, settings.TWO_FACTOR_MAX_ATTEMPTS - challenge.failed_attempts)
        if remaining == 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="تجاوزت عدد المحاولات — اطلب رمزاً جديداً",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"رمز غير صحيح — متبقٍ {remaining} محاولات",
        )
    challenge.used_at = datetime.now(timezone.utc)
    await db.flush()


async def begin_login_challenge(
    db: AsyncSession,
    user: User,
    *,
    ip_address: str | None = None,
    device_name: str | None = None,
) -> dict:
    if not is_two_factor_enabled(user):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="المصادقة الثنائية غير مفعّلة")

    challenge_token, code, row = await _create_challenge(
        db,
        user,
        TwoFactorPurpose.login,
        ip_address=ip_address,
        device_name=device_name,
    )

    provider = get_two_factor_provider(user.two_factor_method)
    try:
        await provider.deliver_code(db, user, code, context="login")
    except EmailDeliveryError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="تعذر إرسال رمز التحقق — حاول لاحقاً",
        )

    return {
        "requires_2fa": True,
        "challenge_token": challenge_token,
        "expires_in_seconds": int((row.expires_at - datetime.now(timezone.utc)).total_seconds()),
        "masked_email": mask_email(user.email),
        "resend_available_in_seconds": settings.TWO_FACTOR_RESEND_COOLDOWN_SECONDS,
    }


async def verify_login_challenge(
    db: AsyncSession,
    challenge_token: str,
    code: str,
    *,
    ip_address: str | None = None,
) -> tuple[User, TwoFactorChallenge]:
    challenge = await _get_active_challenge(db, challenge_token, TwoFactorPurpose.login)
    user = await db.get(User, challenge.user_id)
    if not user or not is_two_factor_enabled(user):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="جلسة التحقق غير صالحة")

    await _verify_code_on_challenge(db, challenge, code)
    await log_audit(
        db,
        action="2fa_login_success",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        ip_address=ip_address,
    )
    return user, challenge


async def resend_login_challenge(
    db: AsyncSession,
    challenge_token: str,
) -> dict:
    challenge = await _get_active_challenge(db, challenge_token, TwoFactorPurpose.login)
    now = datetime.now(timezone.utc)

    if challenge.resend_count >= settings.TWO_FACTOR_MAX_RESENDS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="تجاوزت حد إعادة الإرسال — سجّل الدخول من جديد",
        )

    elapsed = (now - challenge.last_sent_at).total_seconds()
    if elapsed < settings.TWO_FACTOR_RESEND_COOLDOWN_SECONDS:
        wait = int(settings.TWO_FACTOR_RESEND_COOLDOWN_SECONDS - elapsed)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"انتظر {wait} ثانية قبل إعادة الإرسال",
        )

    user = await db.get(User, challenge.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="جلسة التحقق غير صالحة")

    code = _generate_code()
    challenge.code_hash = _hash_value(code)
    challenge.failed_attempts = 0
    challenge.resend_count += 1
    challenge.last_sent_at = now
    challenge.expires_at = now + timedelta(minutes=_expire_minutes())
    await db.flush()

    provider = get_two_factor_provider(user.two_factor_method)
    try:
        await provider.deliver_code(db, user, code, context="login_resend")
    except EmailDeliveryError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="تعذر إرسال رمز التحقق — حاول لاحقاً",
        )

    return {
        "ok": True,
        "detail": "تم إرسال رمز جديد",
        "expires_in_seconds": int((challenge.expires_at - now).total_seconds()),
        "resend_available_in_seconds": settings.TWO_FACTOR_RESEND_COOLDOWN_SECONDS,
    }


async def request_enable_two_factor(
    db: AsyncSession,
    user: User,
    password: str,
    *,
    ip_address: str | None = None,
) -> dict:
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="كلمة المرور غير صحيحة")
    if is_two_factor_enabled(user):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="المصادقة الثنائية مفعّلة بالفعل")

    challenge_token, code, row = await _create_challenge(
        db,
        user,
        TwoFactorPurpose.enable,
        ip_address=ip_address,
    )
    provider = get_two_factor_provider(TwoFactorMethod.email.value)
    try:
        await provider.deliver_code(db, user, code, context="enable")
    except EmailDeliveryError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="تعذر إرسال رمز التحقق — حاول لاحقاً",
        )

    return {
        "ok": True,
        "detail": "تم إرسال رمز التفعيل إلى بريدك",
        "challenge_token": challenge_token,
        "expires_in_seconds": int((row.expires_at - datetime.now(timezone.utc)).total_seconds()),
        "masked_email": mask_email(user.email),
    }


async def confirm_enable_two_factor(
    db: AsyncSession,
    user: User,
    challenge_token: str,
    code: str,
    *,
    ip_address: str | None = None,
) -> User:
    challenge = await _get_active_challenge(db, challenge_token, TwoFactorPurpose.enable)
    if challenge.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="غير مصرح")

    await _verify_code_on_challenge(db, challenge, code)
    user.two_factor_enabled = True
    user.two_factor_method = TwoFactorMethod.email.value
    await db.flush()

    await log_audit(
        db,
        action="2fa_enabled",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        new_values={"method": TwoFactorMethod.email.value},
        ip_address=ip_address,
    )
    return user


async def disable_two_factor(
    db: AsyncSession,
    user: User,
    password: str,
    *,
    ip_address: str | None = None,
) -> User:
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="كلمة المرور غير صحيحة")
    if not is_two_factor_enabled(user):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="المصادقة الثنائية غير مفعّلة")

    user.two_factor_enabled = False
    user.two_factor_method = None
    await db.flush()
    await _invalidate_open_challenges(db, user.id, TwoFactorPurpose.login)

    await log_audit(
        db,
        action="2fa_disabled",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        ip_address=ip_address,
    )
    return user
