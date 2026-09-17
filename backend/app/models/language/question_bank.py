from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.language.enums import LanguageLevel


class LanguagePlacementQuestionBankItem(Base):
    """Reviewed placement-test item bank.

    This table is intentionally broader than the older generated-question bank: it supports
    reading/listening/grammar-vocab anchors plus writing/speaking prompts, boundary items,
    media metadata, review status, and future calibration stats.
    """

    __tablename__ = "language_placement_question_bank_items"
    __table_args__ = (
        Index(
            "ix_lpq_bank_lookup",
            "language_id",
            "skill",
            "level",
            "is_verified",
            "is_active",
        ),
        Index(
            "ix_lpq_bank_boundary",
            "language_id",
            "skill",
            "boundary_low_level",
            "boundary_high_level",
            "is_verified",
            "is_active",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)

    # reading | listening | grammar_vocab | writing_prompt | speaking_prompt
    skill: Mapped[str] = mapped_column(String(32), index=True)
    level: Mapped[LanguageLevel] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e]),
        index=True,
    )

    # Optional boundary target, e.g. A2/B1. Boundary items are better than generic level items
    # when the adaptive engine is deciding between two adjacent CEFR bands.
    boundary_low_level: Mapped[LanguageLevel | None] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    boundary_high_level: Mapped[LanguageLevel | None] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )

    # main_idea | detail | inference | vocabulary_context | reference | tense | collocation ...
    subskill: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    question_type: Mapped[str] = mapped_column(String(32), default="mcq", server_default="mcq")

    prompt_text: Mapped[str] = mapped_column(Text)
    passage: Mapped[str | None] = mapped_column(Text, nullable=True)
    situation: Mapped[str | None] = mapped_column(Text, nullable=True)
    options_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    correct_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    media_object_id: Mapped[int | None] = mapped_column(ForeignKey("media_objects.id", ondelete="SET NULL"), nullable=True)
    audio_meta_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    body_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    stable_key: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="ai_generated", server_default="ai_generated")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    usage_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    correct_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    difficulty_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    discrimination_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
