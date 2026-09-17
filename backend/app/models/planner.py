import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LifeEventType(str, enum.Enum):
    school = "school"
    private_lesson = "private_lesson"
    exam = "exam"
    sport = "sport"
    family = "family"
    social = "social"
    religious = "religious"
    other = "other"


class ScheduleSlotStatus(str, enum.Enum):
    planned = "planned"
    completed = "completed"
    missed = "missed"


class PlannerProfile(Base):
    __tablename__ = "planner_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    preferred_period: Mapped[str] = mapped_column(String(32), default="evening")
    school_start: Mapped[str] = mapped_column(String(8), default="08:00")
    school_end: Mapped[str] = mapped_column(String(8), default="14:00")
    max_daily_minutes: Mapped[int] = mapped_column(Integer, default=120)
    weak_subjects_json: Mapped[str] = mapped_column(Text, default="[]")
    memory_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PlannerLifeEvent(Base):
    __tablename__ = "planner_life_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    event_type: Mapped[LifeEventType] = mapped_column(Enum(LifeEventType), default=LifeEventType.other)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_time: Mapped[str | None] = mapped_column(String(8), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    is_blocking: Mapped[bool] = mapped_column(Boolean, default=True)
    subject: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlannerScheduleSlot(Base):
    __tablename__ = "planner_schedule_slots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(120))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=45)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[ScheduleSlotStatus] = mapped_column(
        Enum(ScheduleSlotStatus), default=ScheduleSlotStatus.planned
    )
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlannerChatMessage(Base):
    __tablename__ = "planner_chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
