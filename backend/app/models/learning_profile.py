"""Long-term student learning memory for lesson chat."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentLearningProfile(Base):
    __tablename__ = "student_learning_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    weak_topics_json: Mapped[str] = mapped_column(Text, default="[]")
    strong_topics_json: Mapped[str] = mapped_column(Text, default="[]")
    repeated_mistakes_json: Mapped[str] = mapped_column(Text, default="[]")
    lesson_history_json: Mapped[str] = mapped_column(Text, default="[]")
    memory_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
