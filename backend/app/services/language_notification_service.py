"""Language module notifications — Phase A: subscription activated only."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationType
from app.services import notification_service
from app.services.integration_hooks import notify_parent_alert


async def notify_language_subscription_activated(db: AsyncSession, *, student_id: int) -> None:
    await notification_service.create_notification(
        db,
        user_id=student_id,
        notification_type=NotificationType.system.value,
        title="Your language learning subscription has been activated",
        body="You can now start the English placement test.",
        payload={"module": "language", "event": "subscription_activated"},
    )
    await notify_parent_alert(
        db,
        student_id=student_id,
        title="Language learning subscription",
        body="The student's language learning subscription has been activated.",
        payload={"module": "language", "event": "subscription_activated"},
    )
