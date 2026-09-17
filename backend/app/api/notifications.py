from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notifications import NotificationListOut, NotificationOut, UnreadCountOut
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListOut)
async def list_my_notifications(
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await notification_service.list_notifications(
        db, user.id, limit=limit, unread_only=unread_only
    )
    unread = await notification_service.unread_count(db, user.id)
    return NotificationListOut(
        items=[NotificationOut(**notification_service.notification_to_dict(n)) for n in rows],
        unread_count=unread,
    )


@router.get("/unread-count", response_model=UnreadCountOut)
async def get_unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await notification_service.unread_count(db, user.id)
    return UnreadCountOut(unread_count=count)


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await notification_service.mark_read(db, user.id, notification_id)
    await db.commit()
    return NotificationOut(**notification_service.notification_to_dict(row))


@router.post("/read-all")
async def mark_all_notifications_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await notification_service.mark_all_read(db, user.id)
    await db.commit()
    return {"ok": True, "marked": count}
