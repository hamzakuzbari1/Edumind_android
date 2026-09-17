"""Per-course student subscriptions (post-registration)."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Course, TeacherProfile
from app.models.enrollment import Payment, PaymentItem, PaymentMethod, PaymentStatus
from app.models.language.enums import PaymentItemProductType
from app.schemas.subscriptions import SubscribeCourseOut
from app.services.audit_service import log_audit
from app.services.payment_service import METHOD_MAP
from app.services.student_courses_service import ensure_course_access
from app.services.user_status_service import get_student_profile


async def subscribe_course(
    db: AsyncSession, student_id: int, course_id: int, method: str = "card"
) -> SubscribeCourseOut:
    profile = await get_student_profile(db, student_id)
    if not profile.grade:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="حدّد صفك أولاً")

    result = await db.execute(
        select(Course)
        .join(TeacherProfile, Course.teacher_profile_id == TeacherProfile.id)
        .where(
            Course.id == course_id,
            Course.grade == profile.grade,
            Course.is_active.is_(True),
            Course.is_published.is_(True),
            TeacherProfile.active.is_(True),
        )
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المادة غير متاحة لصفك")

    from app.services.subscription_access_service import (
        activate_paid_access,
        is_access_active,
        subscription_lifecycle_status,
    )

    now = datetime.now(timezone.utc)
    access = await ensure_course_access(db, student_id, course_id)
    lifecycle = subscription_lifecycle_status(access, now)
    if lifecycle in ("revoked", "suspended"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="الوصول لهذه المادة غير متاح")
    # Fully active (not expiring) stays idempotent. Expiring/expired/pending go through
    # activate_paid_access so a DEV subscribe/renew actually extends the entitlement.
    if (
        access.payment_status == PaymentStatus.paid
        and is_access_active(access, now)
        and lifecycle == "active"
    ):
        return SubscribeCourseOut(ok=True, course_id=course_id, reference="ALREADY-PAID", unlocked=True)

    if method not in METHOD_MAP:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="طريقة دفع غير مدعومة")
    reference = f"SUB-{uuid.uuid4().hex[:12].upper()}"

    payment = Payment(
        student_id=student_id,
        total_amount=course.price,
        currency=course.currency,
        method=METHOD_MAP[method],
        status=PaymentStatus.paid,
        reference=reference,
        paid_at=now,
    )
    db.add(payment)
    await db.flush()
    db.add(
        PaymentItem(
            payment_id=payment.id,
            product_type=PaymentItemProductType.course,
            course_id=course.id,
            unit_price=course.price,
        )
    )

    activate_paid_access(access, now)

    if not profile.payment_completed_at:
        profile.payment_completed_at = now

    await db.flush()
    await log_audit(
        db,
        action="subscription_activated",
        entity_type="subscription",
        entity_id=access.id,
        actor_user_id=student_id,
        new_values={"course_id": course_id, "payment_id": payment.id, "reference": reference},
    )
    from app.services.integration_hooks import after_payment_success, notify_payment_received

    await notify_payment_received(
        db, student_id=student_id, course_title=course.title, amount=float(course.price)
    )
    await after_payment_success(db, student_id, course_id)
    return SubscribeCourseOut(ok=True, course_id=course_id, reference=reference, unlocked=True)
