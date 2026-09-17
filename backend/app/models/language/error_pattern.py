"""Phase 2 — Error Intelligence: recurring learner mistakes aggregated across all sessions.

One row per (student, language, normalized error). `occurrence_count` grows each time the same
mistake recurs; `last_seen` tracks recency for trend analysis. Keyed on integer student/language
ids (same convention as the rest of the language module).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LanguageErrorPattern(Base):
    __tablename__ = "language_error_patterns"
    __table_args__ = (
        UniqueConstraint("student_id", "language_id", "pattern_key", name="uq_language_error_pattern"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)

    error_type: Mapped[str] = mapped_column(String(20))  # grammar|vocabulary|pronunciation|spelling|punctuation
    # Stable dedupe key = f"{error_type}:{normalized(incorrect_form)}" capped to 200 chars.
    pattern_key: Mapped[str] = mapped_column(String(200), index=True)

    incorrect_form: Mapped[str] = mapped_column(Text)
    corrected_form: Mapped[str] = mapped_column(Text, default="")
    context_sentence: Mapped[str | None] = mapped_column(Text, nullable=True)

    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
