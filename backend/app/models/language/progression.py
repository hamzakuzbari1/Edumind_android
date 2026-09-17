"""Official language progression state — authoritative CEFR gate (Phase 4.2.1)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.language.enums import LanguageLevel

_LANGUAGE_LEVEL_ENUM = Enum(
    LanguageLevel,
    name="language_level",
    create_constraint=False,
    values_callable=lambda e: [x.value for x in e],
)


class LanguageProgression(Base):
    """One row per student × language — sole store for Official CEFR (Phase 4.2+)."""

    __tablename__ = "language_progression"

    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    language_id: Mapped[int] = mapped_column(
        ForeignKey("languages.id", ondelete="CASCADE"), primary_key=True
    )
    official_reading_cefr: Mapped[LanguageLevel] = mapped_column(
        _LANGUAGE_LEVEL_ENUM, nullable=False, server_default="A1"
    )
    official_listening_cefr: Mapped[LanguageLevel] = mapped_column(
        _LANGUAGE_LEVEL_ENUM, nullable=False, server_default="A1"
    )
    official_writing_cefr: Mapped[LanguageLevel] = mapped_column(
        _LANGUAGE_LEVEL_ENUM, nullable=False, server_default="A1"
    )
    official_speaking_cefr: Mapped[LanguageLevel] = mapped_column(
        _LANGUAGE_LEVEL_ENUM, nullable=False, server_default="A1"
    )
    official_overall_cefr: Mapped[LanguageLevel] = mapped_column(
        _LANGUAGE_LEVEL_ENUM, nullable=False, server_default="A1"
    )
    learning_stage_reading: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1")
    learning_stage_listening: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1")
    learning_stage_writing: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1")
    learning_stage_speaking: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1")
    promotion_readiness_score: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    promotion_readiness_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    promotion_cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_promotion_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LanguageProgressionEvent(Base):
    """Append-only audit log for progression changes."""

    __tablename__ = "language_progression_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    language_id: Mapped[int] = mapped_column(
        ForeignKey("languages.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
