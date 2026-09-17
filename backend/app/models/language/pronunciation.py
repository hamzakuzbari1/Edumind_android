"""Phase 6 — Advanced pronunciation analysis: stored per-attempt prosody scores for history/trends.

One row per assessed speaking attempt, keyed on integer student/language ids (module convention).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LanguagePronunciationScore(Base):
    __tablename__ = "language_pronunciation_scores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)

    # 0-100 prosody dimensions (overall + the four detailed ones).
    overall: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    clarity: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    fluency: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    pace: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    stress: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    intonation: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    source: Mapped[str] = mapped_column(String(20), default="conversation", server_default="conversation")
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
