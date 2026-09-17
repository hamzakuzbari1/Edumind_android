"""Language Learning Subscription — purchase and access records."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import Payment, PaymentItem, PaymentMethod, PaymentStatus
from app.models.language.catalog import Language, LanguageProduct
from app.models.language.enums import LanguageOnboardingStep, PaymentItemProductType
from app.models.language.profile import LanguageStudentProfile
from app.models.language.subscription import LanguageSubscription
from app.schemas.language import LanguageSubscribeOut
from app.services.audit_service import log_audit
from app.services.language_subscription_access_service import (
    activate_language_subscription,
    is_language_subscription_active,
    language_subscription_status,
)
from app.services.payment_service import METHOD_MAP

DEFAULT_PRODUCT_SLUG = "language_learning"
DEFAULT_LANGUAGE_CODE = "en"


async def get_default_product(db: AsyncSession) -> LanguageProduct:
    result = await db.execute(
        select(LanguageProduct).where(
            LanguageProduct.slug == DEFAULT_PRODUCT_SLUG,
            LanguageProduct.is_active.is_(True),
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The language learning product is currently unavailable",
        )
    return product


async def get_default_language(db: AsyncSession) -> Language:
    result = await db.execute(
        select(Language).where(Language.code == DEFAULT_LANGUAGE_CODE, Language.is_active.is_(True))
    )
    language = result.scalar_one_or_none()
    if not language:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="English is currently not available",
        )
    return language


async def ensure_language_subscription(
    db: AsyncSession, student_id: int, product_id: int
) -> LanguageSubscription:
    result = await db.execute(
        select(LanguageSubscription).where(
            LanguageSubscription.student_id == student_id,
            LanguageSubscription.product_id == product_id,
        )
    )
    sub = result.scalar_one_or_none()
    if sub:
        return sub
    sub = LanguageSubscription(student_id=student_id, product_id=product_id)
    db.add(sub)
    await db.flush()
    return sub


async def ensure_language_profile(db: AsyncSession, student_id: int, language_id: int) -> LanguageStudentProfile:
    result = await db.execute(
        select(LanguageStudentProfile).where(
            LanguageStudentProfile.student_id == student_id,
            LanguageStudentProfile.language_id == language_id,
        )
    )
    profile = result.scalar_one_or_none()
    if profile:
        return profile
    now = datetime.now(timezone.utc)
    profile = LanguageStudentProfile(
        student_id=student_id,
        language_id=language_id,
        onboarding_step=LanguageOnboardingStep.select_language,
        selected_at=now,
    )
    db.add(profile)
    await db.flush()
    return profile


async def get_student_subscription(
    db: AsyncSession, student_id: int, product_id: int | None = None
) -> LanguageSubscription | None:
    if product_id is None:
        product = await get_default_product(db)
        product_id = product.id
    result = await db.execute(
        select(LanguageSubscription).where(
            LanguageSubscription.student_id == student_id,
            LanguageSubscription.product_id == product_id,
        )
    )
    return result.scalar_one_or_none()


async def subscribe_language(db: AsyncSession, student_id: int, method: str = "card") -> LanguageSubscribeOut:
    product = await get_default_product(db)
    language = await get_default_language(db)
    now = datetime.now(timezone.utc)

    sub = await ensure_language_subscription(db, student_id, product.id)
    if sub.payment_status == PaymentStatus.paid and is_language_subscription_active(sub, now):
        return LanguageSubscribeOut(ok=True, reference="ALREADY-PAID", unlocked=True, status="active")

    if method not in METHOD_MAP:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported payment method")

    reference = f"LNG-{uuid.uuid4().hex[:12].upper()}"
    payment = Payment(
        student_id=student_id,
        total_amount=product.price,
        currency=product.currency,
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
            product_type=PaymentItemProductType.language,
            language_product_id=product.id,
            unit_price=product.price,
        )
    )

    activate_language_subscription(sub, now, term_days=product.term_days)
    sub.payment_id = payment.id

    profile = await ensure_language_profile(db, student_id, language.id)
    if profile.onboarding_step == LanguageOnboardingStep.select_language:
        profile.onboarding_step = LanguageOnboardingStep.placement
        profile.selected_at = profile.selected_at or now

    await db.flush()
    await log_audit(
        db,
        action="language_subscription_activated",
        entity_type="language_subscription",
        entity_id=sub.id,
        actor_user_id=student_id,
        new_values={"product_id": product.id, "payment_id": payment.id, "reference": reference},
    )

    from app.services.language_notification_service import notify_language_subscription_activated

    await notify_language_subscription_activated(db, student_id=student_id)

    status_val = language_subscription_status(sub, now)
    return LanguageSubscribeOut(ok=True, reference=reference, unlocked=True, status=status_val)
