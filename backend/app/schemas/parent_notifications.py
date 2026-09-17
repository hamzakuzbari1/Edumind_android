from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


PARENT_NOTIFICATION_TYPE_LABELS: dict[str, str] = {
    "parent_student_login": "دخول الطالب",
    "parent_student_logout": "خروج الطالب",
    "parent_lesson_completed": "إكمال درس",
    "parent_quiz_completed": "إكمال اختبار",
    "parent_low_score": "نتيجة منخفضة",
    "parent_inactivity": "خمول",
    "parent_planner": "مهام المخطط",
    "parent_alert": "تنبيه عام",
}


class ParentNotificationOut(BaseModel):
    id: int
    type: str
    category: str
    category_label: str
    title: str
    body: str
    payload: dict[str, Any] | None = None
    student_id: int | None = None
    is_read: bool
    status: str
    read_at: datetime | None = None
    created_at: datetime | None = None


class ParentNotificationListOut(BaseModel):
    items: list[ParentNotificationOut]
    unread_count: int


class ParentNotificationSettingsOut(BaseModel):
    student_id: int
    login_alerts: bool = True
    logout_alerts: bool = True
    lesson_alerts: bool = True
    quiz_alerts: bool = True
    low_score_alerts: bool = True
    inactivity_alerts: bool = True
    planner_alerts: bool = True
    inactivity_days: int = Field(default=3, ge=1, le=30)
    low_score_threshold: int = Field(default=60, ge=0, le=100)


class ParentNotificationSettingsUpdateIn(BaseModel):
    login_alerts: bool | None = None
    logout_alerts: bool | None = None
    lesson_alerts: bool | None = None
    quiz_alerts: bool | None = None
    low_score_alerts: bool | None = None
    inactivity_alerts: bool | None = None
    planner_alerts: bool | None = None
    inactivity_days: int | None = Field(default=None, ge=1, le=30)
    low_score_threshold: int | None = Field(default=None, ge=0, le=100)
