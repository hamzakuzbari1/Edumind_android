"""Demo payment flow — production-ready records."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import Course
from app.models.enrollment import Payment, PaymentItem, PaymentMethod, PaymentStatus, StudentCourseAccess
from app.schemas.catalog import CoursePreviewOut
from app.schemas.payment import CheckoutOut, DemoCheckoutOut
from app.services.audit_service import log_audit
from app.services.catalog_service import course_summary
from app.services.user_status_service import get_student_profile
from app.utils.media_urls import public_upload_url

METHOD_MAP = {
    "card": PaymentMethod.card,
    "transfer": PaymentMethod.transfer,
    "wallet": PaymentMethod.wallet,
    "cash": PaymentMethod.cash,
}


async def get_checkout(db: AsyncSession, student_id: int) -> CheckoutOut:
    profile = await get_student_profile(db, student_id)
    if not profile.grade:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="حدّد صفك أولاً")

    result = await db.execute(
        select(StudentCourseAccess)
        .where(
            StudentCourseAccess.student_id == student_id,
            StudentCourseAccess.payment_status == PaymentStatus.pending,
        )
        .options(
            selectinload(StudentCourseAccess.course).selectinload(Course.subject),
            selectinload(StudentCourseAccess.course).selectinload(Course.teacher_profile),
        )
    )
    items = []
    total = 0.0
    currency = "SYP"
    for access in result.scalars().all():
        c = access.course
        currency = c.currency
        total += c.price
        items.append(
            CoursePreviewOut(
                id=c.id,
                title=c.title,
                subject_name=c.subject.name_ar,
                teacher_name=c.teacher_profile.full_name,
                teacher_image_url=public_upload_url(c.teacher_profile.image_url),
                summary=course_summary(c),
                grade=c.grade,
                price=c.price,
                currency=c.currency,
            )
        )
    return CheckoutOut(items=items, total_amount=round(total, 2), currency=currency)


async def demo_checkout(db: AsyncSession, student_id: int, method: str) -> DemoCheckoutOut:
    checkout = await get_checkout(db, student_id)
    if not checkout.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا توجد دورات للدفع")

    profile = await get_student_profile(db, student_id)
    now = datetime.now(timezone.utc)
    reference = f"PAY-{uuid.uuid4().hex[:12].upper()}"

    payment = Payment(
        student_id=student_id,
        total_amount=checkout.total_amount,
        currency=checkout.currency,
        method=METHOD_MAP[method],
        status=PaymentStatus.paid,
        reference=reference,
        paid_at=now,
    )
    db.add(payment)
    await db.flush()

    for item in checkout.items:
        from app.models.language.enums import PaymentItemProductType

        db.add(
            PaymentItem(
                payment_id=payment.id,
                product_type=PaymentItemProductType.course,
                course_id=item.id,
                unit_price=item.price,
            )
        )
        access_result = await db.execute(
            select(StudentCourseAccess).where(
                StudentCourseAccess.student_id == student_id,
                StudentCourseAccess.course_id == item.id,
            )
        )
        access = access_result.scalar_one_or_none()
        if access:
            from app.services.subscription_access_service import activate_paid_access

            activate_paid_access(access, now)

    profile.payment_completed_at = now
    await db.flush()
    await log_audit(
        db,
        action="payment_completed",
        entity_type="payment",
        entity_id=payment.id,
        actor_user_id=student_id,
        new_values={
            "reference": reference,
            "total_amount": checkout.total_amount,
            "course_ids": [item.id for item in checkout.items],
        },
    )
    from app.services.integration_hooks import after_payment_success, notify_payment_received

    for item in checkout.items:
        course = await db.get(Course, item.id)
        title = course.title if course else "المادة"
        await notify_payment_received(
            db, student_id=student_id, course_title=title, amount=float(item.price)
        )
        await after_payment_success(db, student_id, item.id)

    return DemoCheckoutOut(
        payment_id=payment.id,
        reference=reference,
        total_amount=checkout.total_amount,
        currency=checkout.currency,
        unlocked_items=checkout.items,
    )
