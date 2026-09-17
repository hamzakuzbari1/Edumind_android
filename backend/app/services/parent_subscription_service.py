"""Parent dashboard: subscription status per linked student."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import Course
from app.models.enrollment import PaymentStatus, StudentCourseAccess
from app.schemas.parent import StudentSubscriptionStatusOut
from app.services.subscription_access_service import (
    days_until_expiry,
    subscription_lifecycle_status,
    _aware,
)


async def list_student_subscription_status(
    db: AsyncSession, student_id: int
) -> list[StudentSubscriptionStatusOut]:
    result = await db.execute(
        select(StudentCourseAccess)
        .where(
            StudentCourseAccess.student_id == student_id,
            StudentCourseAccess.payment_status == PaymentStatus.paid,
        )
        .options(selectinload(StudentCourseAccess.course).selectinload(Course.subject))
        .order_by(StudentCourseAccess.expires_at.asc().nullslast())
    )
    items: list[StudentSubscriptionStatusOut] = []
    for access in result.scalars().all():
        course = access.course
        status = subscription_lifecycle_status(access)
        activated = _aware(access.activated_at)
        expires = _aware(access.expires_at)
        items.append(
            StudentSubscriptionStatusOut(
                course_id=access.course_id,
                course_title=course.title if course else "—",
                subject_name=course.subject.name_ar if course and course.subject else "",
                subscription_status=status,
                activated_at=activated.isoformat() if activated else None,
                expires_at=expires.isoformat() if expires else None,
                days_until_expiry=days_until_expiry(access)
                if status in ("active", "expiring_soon")
                else None,
            )
        )
    return items
