"""Phase 11 — daily progress snapshots, so analytics can show change over time.

One row per (student, language, day). Written idempotently when the learner loads their daily plan,
so the series accumulates without a background job. Integer keys (module convention).
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LanguageProgressSnapshot(Base):
    __tablename__ = "language_progress_snapshots"
    __table_args__ = (
        UniqueConstraint("student_id", "language_id", "snapshot_date", name="uq_language_progress_snapshot"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)

    # CEFR ranks 1-6 (0 = unknown).
    overall_rank: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reading_rank: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    listening_rank: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    writing_rank: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    speaking_rank: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    xp_total: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    vocabulary_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    pronunciation_avg: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
