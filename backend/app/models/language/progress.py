from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.language.enums import LanguageContentProgressStatus, LanguageLevel, LanguageVocabularyStatus


class LanguageReadingProgress(Base):
    __tablename__ = "language_reading_progress"
    __table_args__ = (UniqueConstraint("student_id", "content_item_id", name="uq_language_reading_progress"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content_item_id: Mapped[int] = mapped_column(ForeignKey("language_content_items.id", ondelete="CASCADE"), index=True)
    status: Mapped[LanguageContentProgressStatus] = mapped_column(
        Enum(
            LanguageContentProgressStatus,
            name="language_content_progress_status",
            create_constraint=False,
            values_callable=lambda e: [x.value for x in e],
        ),
        default=LanguageContentProgressStatus.not_started,
    )
    score_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class LanguageListeningProgress(Base):
    __tablename__ = "language_listening_progress"
    __table_args__ = (UniqueConstraint("student_id", "content_item_id", name="uq_language_listening_progress"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content_item_id: Mapped[int] = mapped_column(ForeignKey("language_content_items.id", ondelete="CASCADE"), index=True)
    status: Mapped[LanguageContentProgressStatus] = mapped_column(
        Enum(
            LanguageContentProgressStatus,
            name="language_content_progress_status",
            create_constraint=False,
            values_callable=lambda e: [x.value for x in e],
        ),
        default=LanguageContentProgressStatus.not_started,
    )
    score_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class LanguageWritingProgress(Base):
    __tablename__ = "language_writing_progress"
    __table_args__ = (UniqueConstraint("student_id", "content_item_id", name="uq_language_writing_progress"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content_item_id: Mapped[int] = mapped_column(ForeignKey("language_content_items.id", ondelete="CASCADE"), index=True)
    submitted_text: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    score_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metrics_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    level_estimate: Mapped[LanguageLevel | None] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    scoring_version: Mapped[str] = mapped_column(String(32), default="rule_v1")
    ai_evaluation_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LanguageSpeakingProgress(Base):
    __tablename__ = "language_speaking_progress"
    __table_args__ = (UniqueConstraint("student_id", "content_item_id", name="uq_language_speaking_progress"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content_item_id: Mapped[int] = mapped_column(ForeignKey("language_content_items.id", ondelete="CASCADE"), index=True)
    media_object_id: Mapped[int] = mapped_column(ForeignKey("media_objects.id", ondelete="CASCADE"), index=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    level_estimate: Mapped[LanguageLevel | None] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    scoring_version: Mapped[str] = mapped_column(String(32), default="rule_v1")
    ai_evaluation_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LanguageVocabularyProgress(Base):
    __tablename__ = "language_vocabulary_progress"
    __table_args__ = (UniqueConstraint("student_id", "language_id", "lemma", name="uq_language_vocab"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    lemma: Mapped[str] = mapped_column(String(120))
    status: Mapped[LanguageVocabularyStatus] = mapped_column(
        Enum(
            LanguageVocabularyStatus,
            name="language_vocabulary_status",
            create_constraint=False,
            values_callable=lambda e: [x.value for x in e],
        ),
        default=LanguageVocabularyStatus.new,
    )
    review_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    mastery_score: Mapped[float] = mapped_column(Float, default=0)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    interval_days: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, server_default="2.5")
    repetition_number: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_difficult: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    fail_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    consecutive_good_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class LanguageCurriculumProgress(Base):
    __tablename__ = "language_curriculum_progress"
    __table_args__ = (UniqueConstraint("student_id", "objective_id", name="uq_language_curriculum_progress"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    objective_id: Mapped[str] = mapped_column(String(48), index=True)
    status: Mapped[str] = mapped_column(String(16), default="new", server_default="new")
    practice_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_practiced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mastered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
