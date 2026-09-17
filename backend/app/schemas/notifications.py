from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    body: str
    payload: dict[str, Any] | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime | None = None


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    unread_count: int


class UnreadCountOut(BaseModel):
    unread_count: int = 0
