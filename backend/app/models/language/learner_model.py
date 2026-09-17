"""Unified Learner Model — the new source of truth for fine-grained skill knowledge.

Coexists with `LanguageAnalytics` (which stays the display/UI layer and is kept in sync). Every
feature writes evidence here via `LanguageLearnerModelService.process_event()`; nothing accesses
these tables directly.

- `KnowledgeComponent`  — a reference catalogue of teachable units (e.g. "grammar.present_perfect").
                          Shared across students; not per-student.
- `ComponentMastery`    — per-(student, language, component) mastery: BKT `p_mastery` + confidence
                          + SM-2 scheduling (field names match `compute_sm2`).

Anchor decision: `ComponentMastery` keys on (student_id, language_id) — the SAME composite key as
`LanguageAnalytics` — so there is NO separate `LearnerModel` parent row (analytics already is the
per-(student, language) row; a parent would just duplicate it).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.language.enums import LanguageLevel, LanguageSkill


class KnowledgeComponent(Base):
    """A single teachable knowledge unit (reference data, shared across students)."""

    __tablename__ = "language_knowledge_components"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # e.g. "grammar.present_perfect"
    display_skill: Mapped[LanguageSkill] = mapped_column(
        Enum(LanguageSkill, name="language_skill", create_constraint=False, values_callable=lambda e: [x.value for x in e])
    )
    category: Mapped[str] = mapped_column(String(32))  # free-form: grammar / vocabulary / pragmatics ...
    cefr_level: Mapped[LanguageLevel] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e])
    )
    prerequisites: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # list[str] of component codes
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LanguageGeneratedQuestion(Base):
    """AI-generated, verified question bank — tagged by component + CEFR (for adaptive selection).

    Placement questions are generated OFFLINE and pass a second-LLM verification before storage
    (verified=True). Used by the adaptive engine; answering them feeds the Learner Model.
    """

    __tablename__ = "language_generated_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    component_code: Mapped[str] = mapped_column(String(64), index=True)
    display_skill: Mapped[LanguageSkill] = mapped_column(
        Enum(LanguageSkill, name="language_skill", create_constraint=False, values_callable=lambda e: [x.value for x in e])
    )
    cefr_level: Mapped[LanguageLevel] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e])
    )
    question_type: Mapped[str] = mapped_column(String(32), default="mcq")
    prompt_json: Mapped[dict] = mapped_column(JSONB)  # {stem, choices[4], correct_index}
    source: Mapped[str] = mapped_column(String(16), default="placement")  # placement | daily
    verified: Mapped[bool] = mapped_column(default=False, server_default="false")
    verification_note: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ComponentMastery(Base):
    """Per-student mastery of one knowledge component — the new source of truth."""

    __tablename__ = "language_component_mastery"
    __table_args__ = (
        UniqueConstraint("student_id", "language_id", "component_id", name="uq_language_component_mastery"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Anchor: same composite key as LanguageAnalytics (student_id, language_id).
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    component_id: Mapped[int] = mapped_column(
        ForeignKey("language_knowledge_components.id", ondelete="CASCADE"), index=True
    )

    # Bayesian Knowledge Tracing — probability the learner has mastered the component.
    p_mastery: Mapped[float] = mapped_column(Float, default=0.1, server_default="0.1")
    # How much we trust p_mastery (grows with evidence).
    confidence: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # SM-2 spaced repetition — field names match compute_sm2() so we can feed it directly.
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, server_default="2.5")
    interval_days: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    repetition_number: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Weight of the strongest evidence source seen (placement evidence > casual practice).
    source_weight: Mapped[float] = mapped_column(Float, default=1.0, server_default="1.0")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
