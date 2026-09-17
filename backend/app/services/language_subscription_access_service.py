"""Language subscription lifecycle — mirrors course subscription_access_service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from app.core.config import get_settings
from app.models.enrollment import PaymentStatus
from app.models.language.subscription import LanguageSubscription

LanguageLifecycleStatus = Literal["pending", "active", "expiring_soon", "expired"]

settings = get_settings()


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def compute_language_expires_at(activated_at: datetime, *, term_days: int | None = None) -> datetime:
    base = _aware(activated_at) or datetime.now(timezone.utc)
    days = term_days if term_days is not None else settings.LANGUAGE_SUBSCRIPTION_TERM_DAYS
    return base + timedelta(days=days)


def activate_language_subscription(
    sub: LanguageSubscription, now: datetime | None = None, *, term_days: int | None = None
) -> None:
    now = _aware(now) or datetime.now(timezone.utc)
    extend = (
        sub.payment_status == PaymentStatus.paid
        and is_language_subscription_active(sub, now)
        and _aware(sub.expires_at) is not None
    )
    sub.payment_status = PaymentStatus.paid
    if extend:
        base = _aware(sub.expires_at)
        assert base is not None
        days = term_days if term_days is not None else settings.LANGUAGE_SUBSCRIPTION_TERM_DAYS
        sub.expires_at = base + timedelta(days=days)
    else:
        sub.activated_at = now
        sub.expires_at = compute_language_expires_at(now, term_days=term_days)


def is_language_subscription_active(
    sub: LanguageSubscription | None, now: datetime | None = None
) -> bool:
    if sub is None or sub.payment_status != PaymentStatus.paid:
        return False
    expires = _aware(sub.expires_at)
    if expires is None:
        return True
    now = _aware(now) or datetime.now(timezone.utc)
    return expires > now


def days_until_language_expiry(sub: LanguageSubscription, now: datetime | None = None) -> int | None:
    expires = _aware(sub.expires_at)
    if expires is None:
        return None
    now = _aware(now) or datetime.now(timezone.utc)
    return max(0, (expires - now).days)


def language_subscription_status(
    sub: LanguageSubscription | None, now: datetime | None = None
) -> LanguageLifecycleStatus:
    if sub is None or sub.payment_status == PaymentStatus.pending:
        return "pending"
    if sub.payment_status != PaymentStatus.paid:
        return "pending"
    if not is_language_subscription_active(sub, now):
        return "expired"
    days = days_until_language_expiry(sub, now)
    if days is not None and days <= settings.LANGUAGE_SUBSCRIPTION_EXPIRING_SOON_DAYS:
        return "expiring_soon"
    return "active"
