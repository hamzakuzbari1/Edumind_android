"""Student activity sessions and engagement events — real study-time foundation."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ActivitySessionLogoutReason(str, enum.Enum):
    logout = "logout"
    expired = "expired"
    inactivity = "inactivity"


class EngagementEventType(str, enum.Enum):
    login = "login"
    logout = "logout"
    session_expired = "session_expired"
    session_inactive = "session_inactive"
    lesson_opened = "lesson_opened"
    lesson_viewed = "lesson_viewed"
    lesson_completed = "lesson_completed"
    quiz_started = "quiz_started"
    quiz_submitted = "quiz_submitted"
    planner_activity = "planner_activity"
    messaging_activity = "messaging_activity"
    page_navigation = "page_navigation"


class StudentActivitySession(Base):
    __tablename__ = "student_activity_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    auth_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("auth_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    logout_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    logout_reason: Mapped[ActivitySessionLogoutReason | None] = mapped_column(
        Enum(ActivitySessionLogoutReason), nullable=True
    )
    active_minutes: Mapped[int] = mapped_column(Integer, default=0)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class StudentEngagementEvent(Base):
    __tablename__ = "student_engagement_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    activity_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("student_activity_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[EngagementEventType] = mapped_column(Enum(EngagementEventType), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    counted_seconds: Mapped[int] = mapped_column(Integer, default=0)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
