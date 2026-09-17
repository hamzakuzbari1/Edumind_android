"""Subscription access rules: activation, expiry, and status classification."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.enrollment import CourseAccessStatus, PaymentStatus, StudentCourseAccess

SubscriptionLifecycleStatus = Literal["pending", "active", "expiring_soon", "expired", "suspended", "revoked"]

COMMUNICATION_REQUIRES_ENROLLMENT = "التواصل متاح فقط للطلاب المشتركين في المادة"

settings = get_settings()


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def compute_expires_at(activated_at: datetime, *, term_days: int | None = None) -> datetime:
    base = _aware(activated_at) or datetime.now(timezone.utc)
    days = term_days if term_days is not None else settings.SUBSCRIPTION_TERM_DAYS
    return base + timedelta(days=days)


def activate_paid_access(access: StudentCourseAccess, now: datetime | None = None) -> None:
    """Mark access paid and set/extend activation window (renewal restores access)."""
    now = _aware(now) or datetime.now(timezone.utc)
    current_status = (access.access_status or "").strip()
    if current_status in {CourseAccessStatus.revoked.value, CourseAccessStatus.suspended.value}:
        return

    extend_from_current = (
        access.payment_status == PaymentStatus.paid
        and is_access_active(access, now)
        and _aware(access.expires_at) is not None
    )
    access.payment_status = PaymentStatus.paid
    access.access_status = CourseAccessStatus.active.value
    access.source = access.source or "payment"
    access.unlocked_at = access.unlocked_at or now
    access.revoked_at = None
    access.revocation_reason = None

    if extend_from_current:
        base = _aware(access.expires_at)
        assert base is not None
        access.expires_at = base + timedelta(days=settings.SUBSCRIPTION_TERM_DAYS)
    else:
        access.activated_at = now
        access.expires_at = compute_expires_at(now)


def is_access_active(access: StudentCourseAccess | None, now: datetime | None = None) -> bool:
    if access is None:
        return False
    access_status = (access.access_status or "").strip()
    if access_status:
        if access_status != CourseAccessStatus.active.value:
            return False
        if _aware(access.revoked_at) is not None:
            return False
    elif access.payment_status != PaymentStatus.paid:
        return False
    expires = _aware(access.expires_at)
    if expires is None:
        return True
    now = _aware(now) or datetime.now(timezone.utc)
    return expires > now


def days_until_expiry(access: StudentCourseAccess, now: datetime | None = None) -> int | None:
    expires = _aware(access.expires_at)
    if expires is None:
        return None
    now = _aware(now) or datetime.now(timezone.utc)
    delta = expires - now
    return max(0, delta.days)


def subscription_lifecycle_status(
    access: StudentCourseAccess | None,
    now: datetime | None = None,
) -> SubscriptionLifecycleStatus:
    if access is None:
        return "pending"
    access_status = (access.access_status or "").strip()
    if access_status in {CourseAccessStatus.revoked.value, CourseAccessStatus.suspended.value}:
        return access_status  # type: ignore[return-value]
    if access_status == CourseAccessStatus.expired.value:
        return "expired"
    if access_status == CourseAccessStatus.pending.value:
        return "pending"
    if not access_status and access.payment_status != PaymentStatus.paid:
        return "pending"
    if not is_access_active(access, now):
        return "expired"
    days = days_until_expiry(access, now)
    if days is not None and days <= settings.SUBSCRIPTION_EXPIRING_SOON_DAYS:
        return "expiring_soon"
    return "active"


def access_to_public_fields(access: StudentCourseAccess, course_title: str = "") -> dict:
    status = subscription_lifecycle_status(access)
    activated = _aware(access.activated_at)
    expires = _aware(access.expires_at)
    days = days_until_expiry(access) if status in ("active", "expiring_soon") else 0
    return {
        "access_id": access.id,
        "course_id": access.course_id,
        "course_title": course_title,
        "subscription_status": status,
        "activated_at": activated.isoformat() if activated else None,
        "expires_at": expires.isoformat() if expires else None,
        "days_until_expiry": days,
        "is_active": status == "active" or status == "expiring_soon",
    }


async def fetch_student_course_access(
    db: AsyncSession, student_id: int, course_id: int
) -> StudentCourseAccess | None:
    return await db.scalar(
        select(StudentCourseAccess).where(
            StudentCourseAccess.student_id == student_id,
            StudentCourseAccess.course_id == course_id,
        )
    )


async def student_has_active_enrollment(
    db: AsyncSession, student_id: int, course_id: int
) -> bool:
    access = await fetch_student_course_access(db, student_id, course_id)
    return is_access_active(access)


async def assert_student_active_enrollment(
    db: AsyncSession, student_id: int, course_id: int
) -> None:
    if not await student_has_active_enrollment(db, student_id, course_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=COMMUNICATION_REQUIRES_ENROLLMENT,
        )
