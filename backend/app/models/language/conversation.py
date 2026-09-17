"""AI speaking conversation sessions and per-turn evaluations."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.language.enums import LanguageLevel


class LanguageSpeakingConversationSession(Base):
    __tablename__ = "language_speaking_conversation_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active", index=True)
    scenario_id: Mapped[int | None] = mapped_column(
        ForeignKey("language_conversation_scenarios.id", ondelete="SET NULL"), nullable=True
    )
    effective_level_at_start: Mapped[LanguageLevel | None] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    turn_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    summary_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    turns: Mapped[list["LanguageSpeakingConversationTurn"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="LanguageSpeakingConversationTurn.turn_index",
    )


class LanguageSpeakingConversationTurn(Base):
    __tablename__ = "language_speaking_conversation_turns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("language_speaking_conversation_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    turn_index: Mapped[int] = mapped_column(Integer)
    user_transcript: Mapped[str] = mapped_column(Text, default="")
    assistant_reply: Mapped[str] = mapped_column(Text, default="")
    user_media_object_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_objects.id", ondelete="SET NULL"),
        nullable=True,
    )
    reply_media_object_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_objects.id", ondelete="SET NULL"),
        nullable=True,
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluation_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    estimated_cefr: Mapped[LanguageLevel | None] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    scoring_version: Mapped[str] = mapped_column(String(32), default="conversation_v1", server_default="conversation_v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["LanguageSpeakingConversationSession"] = relationship(back_populates="turns")
