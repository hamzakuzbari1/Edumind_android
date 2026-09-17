import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ActivityEventType(str, enum.Enum):
    quiz_submitted = "quiz_submitted"
    study_session_completed = "study_session_completed"
    study_streak = "study_streak"
    no_study_today = "no_study_today"
    planner_generated = "planner_generated"
    weak_subject_alert = "weak_subject_alert"
    lesson_activity = "lesson_activity"
    performance_improved = "performance_improved"
    weekly_summary = "weekly_summary"


class StudentActivityEvent(Base):
    __tablename__ = "student_activity_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[ActivityEventType] = mapped_column(Enum(ActivityEventType), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
