"""Wave D — durable grammar activity sessions + append-only evidence ledger."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

JSONB_TYPE = JSON().with_variant(JSONB, "postgresql")
UUID_TYPE = Uuid(as_uuid=True)


class GrammarActivitySession(Base):
    """Server-owned activity session binding student + grammar stamp + content."""

    __tablename__ = "grammar_activity_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    grammar_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    skill: Mapped[str] = mapped_column(String(64), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    lesson_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    content_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    published_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE,
        ForeignKey("grammar_canonical_lesson_revisions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", server_default="open")
    stamp_token: Mapped[str] = mapped_column(Text, nullable=False)
    curriculum_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.1.0")
    # Server-only evaluation aids (answer keys, blanks_mapping) — never trust client copies.
    server_payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB_TYPE, nullable=False, default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    published_revision: Mapped["GrammarCanonicalLessonRevision | None"] = relationship(
        "GrammarCanonicalLessonRevision"
    )


class GrammarEvidenceLedger(Base):
    """Append-only evidence ledger — unique (student_id, observation_id) = replay protection."""

    __tablename__ = "grammar_evidence_ledger"
    __table_args__ = (
        UniqueConstraint("student_id", "observation_id", name="uq_grammar_evidence_ledger_student_obs"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    observation_id: Mapped[str] = mapped_column(String(191), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    grammar_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    activity_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE,
        ForeignKey("grammar_activity_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lesson_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    activity_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    skill: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    curriculum_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.1.0")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
