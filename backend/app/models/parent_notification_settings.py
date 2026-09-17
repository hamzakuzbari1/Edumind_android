from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ParentNotificationSettings(Base):
    """Per parent–student notification preferences (in-app channel today; extensible)."""

    __tablename__ = "parent_notification_settings"
    __table_args__ = (UniqueConstraint("parent_id", "student_id", name="uq_parent_notification_settings"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    login_alerts: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    logout_alerts: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    lesson_alerts: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    quiz_alerts: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    low_score_alerts: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    inactivity_alerts: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    planner_alerts: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    inactivity_days: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    low_score_threshold: Mapped[int] = mapped_column(Integer, default=60, server_default="60")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
