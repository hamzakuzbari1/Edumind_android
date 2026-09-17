"""Language subscription expiry notifications — mirrors course expiration loop."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.enrollment import PaymentStatus
from app.models.language.subscription import LanguageSubscription
from app.models.notification import Notification, NotificationType
from app.services import notification_service
from app.services.integration_hooks import notify_parent_alert
from app.services.language_subscription_access_service import days_until_language_expiry
from app.services.subscription_access_service import _aware as course_aware

logger = logging.getLogger(__name__)
settings = get_settings()
EXPIRY_ALERT_DAYS = (7, 3, 1)


async def _notification_exists(
    db: AsyncSession, *, user_id: int, notification_type: str, sub_id: int, marker: str
) -> bool:
    result = await db.execute(
        select(Notification.id)
        .where(
            Notification.user_id == user_id,
            Notification.type == notification_type,
            Notification.payload.contains({"language_subscription_id": sub_id, "marker": marker}),
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def run_language_expiration_check(db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    stats = {"warnings": 0, "expired": 0}
    result = await db.execute(
        select(LanguageSubscription)
        .where(LanguageSubscription.payment_status == PaymentStatus.paid)
        .options(selectinload(LanguageSubscription.product))
    )
    subs = result.scalars().all()
    for sub in subs:
        expires = course_aware(sub.expires_at)
        if expires is None:
            continue
        days_left = days_until_language_expiry(sub, now)
        if days_left is None:
            continue
        product_name = sub.product.name_ar if sub.product else "Learn the language"
        if days_left <= 0:
            marker = "expired"
            ntype = NotificationType.subscription_expired.value
            if not await _notification_exists(
                db, user_id=sub.student_id, notification_type=ntype, sub_id=sub.id, marker=marker
            ):
                await notification_service.create_notification(
                    db,
                    user_id=sub.student_id,
                    notification_type=ntype,
                    title="Your language learning subscription has expired",
                    body=f"Subscription has expired {product_name}. Renew your subscription forContinue.",
                    payload={"language_subscription_id": sub.id, "marker": marker},
                )
                await notify_parent_alert(
                    db,
                    student_id=sub.student_id,
                    title="Language subscription expires",
                    body=f"Subscription has expired {product_name} For the student.",
                    payload={"module": "language", "marker": marker},
                )
                stats["expired"] += 1
            continue
        for d in EXPIRY_ALERT_DAYS:
            if days_left == d:
                marker = f"expiring_d{d}"
                ntype = NotificationType.subscription_expiring.value
                if await _notification_exists(
                    db, user_id=sub.student_id, notification_type=ntype, sub_id=sub.id, marker=marker
                ):
                    continue
                await notification_service.create_notification(
                    db,
                    user_id=sub.student_id,
                    notification_type=ntype,
                    title=f"Language subscription expires in {d} days",
                    body=f"subscription {product_name} Ends soon.",
                    payload={"language_subscription_id": sub.id, "marker": marker, "days_left": d},
                )
                await notify_parent_alert(
                    db,
                    student_id=sub.student_id,
                    title="Language subscription alert",
                    body=f"Subscription expires {product_name} during {d} days.",
                    payload={"module": "language", "marker": marker},
                )
                stats["warnings"] += 1
    return stats
