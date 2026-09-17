"""Analytics rollup tables — refreshed by background jobs, not per-request."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CourseAnalytics(Base):
    __tablename__ = "course_analytics"

    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    student_count: Mapped[int] = mapped_column(Integer, default=0)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    average_quiz_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    active_students: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TeacherAnalytics(Base):
    __tablename__ = "teacher_analytics"

    teacher_profile_id: Mapped[int] = mapped_column(
        ForeignKey("teacher_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    total_students: Mapped[int] = mapped_column(Integer, default=0)
    total_courses: Mapped[int] = mapped_column(Integer, default=0)
    average_completion: Mapped[float] = mapped_column(Float, default=0.0)
    average_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class StudentAnalytics(Base):
    __tablename__ = "student_analytics"

    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    average_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_study_hours: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
