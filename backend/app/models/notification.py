import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationChannel(str, enum.Enum):
    in_app = "in_app"
    email = "email"
    sms = "sms"
    whatsapp = "whatsapp"


class NotificationType(str, enum.Enum):
    system = "system"
    system_message = "system_message"
    subscription = "subscription"
    subscription_expiring = "subscription_expiring"
    subscription_expired = "subscription_expired"
    attendance = "attendance"
    quiz = "quiz"
    quiz_published = "quiz_published"
    homework = "homework"
    homework_assigned = "homework_assigned"
    homework_graded = "homework_graded"
    lesson_published = "lesson_published"
    payment_received = "payment_received"
    parent_alert = "parent_alert"
    parent_student_login = "parent_student_login"
    parent_student_logout = "parent_student_logout"
    parent_lesson_completed = "parent_lesson_completed"
    parent_quiz_completed = "parent_quiz_completed"
    parent_low_score = "parent_low_score"
    parent_inactivity = "parent_inactivity"
    parent_planner = "parent_planner"
    parent_note = "parent_note"
    parent_note_read = "parent_note_read"
    parent_note_reply = "parent_note_reply"
    internal_message = "internal_message"
    recommendation = "recommendation"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel), default=NotificationChannel.in_app)
    type: Mapped[str] = mapped_column(String(64), default=NotificationType.system.value, index=True)

    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
