"""Daily routine models — full life schedule per student."""
import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ActivityType(str, enum.Enum):
    school = "school"
    study = "study"
    sport = "sport"
    meal = "meal"
    sleep = "sleep"
    prayer = "prayer"
    family = "family"
    private_lesson = "private_lesson"
    free = "free"
    other = "other"


class StudentRoutineProfile(Base):
    __tablename__ = "student_routine_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True)
    grade_level: Mapped[str] = mapped_column(String(20), default="")
    school_start: Mapped[str] = mapped_column(String(8), default="07:30")
    school_end: Mapped[str] = mapped_column(String(8), default="13:00")
    wake_time: Mapped[str] = mapped_column(String(8), default="06:30")
    sleep_time: Mapped[str] = mapped_column(String(8), default="22:00")
    school_days_json: Mapped[str] = mapped_column(Text, default="[1,2,3,4,0]")
    activities_json: Mapped[str] = mapped_column(Text, default="{}")
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    chat_history_json: Mapped[str] = mapped_column(Text, default="[]")
    chat_stage: Mapped[str] = mapped_column(String(32), default="start")
    day_data_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[str] = mapped_column(Text, server_default=func.now())

    slots: Mapped[list["RoutineSlot"]] = relationship(back_populates="profile", cascade="all, delete-orphan")


class RoutineSlot(Base):
    __tablename__ = "routine_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(Integer, ForeignKey("student_routine_profiles.id"))
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0=Mon...6=Sun
    start_time: Mapped[str] = mapped_column(String(8))
    end_time: Mapped[str] = mapped_column(String(8))
    activity_type: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_fixed: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="planned", server_default="planned")

    profile: Mapped["StudentRoutineProfile"] = relationship(back_populates="slots")
