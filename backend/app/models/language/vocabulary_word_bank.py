"""Fixed, per-level vocabulary word bank — one deterministic word set per CEFR level,
pre-generated once (see scripts/seed_vocabulary_word_bank.py) and shared by every student.

Replaces the old (never-populated) offline `LanguageVocabularyCatalog`. Per-student
"have I seen this word" is answered via `LanguageVocabularyProgress.lemma` (which already
matches `word` here 1:1) — no separate seen-tracking table needed.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.language.enums import LanguageLevel


class LanguageVocabularyWordBank(Base):
    __tablename__ = "language_vocabulary_word_bank"
    __table_args__ = (
        UniqueConstraint("word", "cefr_level", name="uq_language_vocabulary_word_bank_word_level"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cefr_level: Mapped[LanguageLevel] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e]),
        index=True,
    )
    word: Mapped[str] = mapped_column(String(80), index=True)  # normalized lemma
    part_of_speech: Mapped[str] = mapped_column(String(40), default="", server_default="")
    translation_ar: Mapped[str] = mapped_column(Text, default="", server_default="")
    definition: Mapped[str] = mapped_column(Text, default="", server_default="")
    example_sentence: Mapped[str] = mapped_column(Text, default="", server_default="")
    example_sentence_ar: Mapped[str] = mapped_column(Text, default="", server_default="")
    image_prompt: Mapped[str] = mapped_column(Text, default="", server_default="")
    topic: Mapped[str] = mapped_column(String(60), default="", server_default="", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
