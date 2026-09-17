"""Precomputed parent-facing grade/course metrics."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentGradeReport(Base):
    __tablename__ = "student_grade_reports"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_student_grade_report"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    average_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    attendance_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    completion_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
