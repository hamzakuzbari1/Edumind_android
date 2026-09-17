"""Student progress on course lessons — granular completion tracking."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StudentLessonProgress(Base):
    __tablename__ = "student_lesson_progress"
    __table_args__ = (UniqueConstraint("student_id", "lesson_id", name="uq_student_lesson_progress"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    video_progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    pdf_progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    pdf_opened: Mapped[bool] = mapped_column(Boolean, default=False)
    quiz_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    quiz_score_percent: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    video_last_watched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completion_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    completion_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    lesson: Mapped["Lesson"] = relationship()

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None
