"""Interactive AI English exam — a fast, 4-turn chat assessment.

Distinct from the multi-step placement wizard: this is a 3-5 minute, chat-style exam where an
AI examiner improvises a unique role-play scenario, asks 4 contextual questions, then produces a
structured academic report (graded asynchronously). One row per exam attempt.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _new_uuid() -> str:
    return uuid.uuid4().hex


class LanguageExamSession(Base):
    """A single interactive AI-exam attempt for a student."""

    __tablename__ = "language_exam_sessions"

    # UUID primary key (string form — portable, no DB extension required).
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language_id: Mapped[int] = mapped_column(
        ForeignKey("languages.id", ondelete="CASCADE"), nullable=False
    )

    current_step: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    max_steps: Mapped[int] = mapped_column(Integer, default=6, server_default="6", nullable=False)

    # The improvised exam world: {"scenario": str, "ai_persona": str, "student_role": str, "setting": str}.
    scenario_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Ordered transcript: [{"role": "examiner"|"student", "content": str}, ...].
    chat_history: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Full multi-skill exam state (v2): section order, cursor, and per-section progress/answers.
    # See language_exam_service for the structure. Older text-only exams leave this NULL.
    exam_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Lifecycle: in_progress -> evaluating -> completed (or failed if grading errored).
    status: Mapped[str] = mapped_column(String(20), default="in_progress", server_default="in_progress", nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    # The structured FinalAcademicReportSchema, persisted once graded.
    assessment_report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    student = relationship("User", lazy="raise")
