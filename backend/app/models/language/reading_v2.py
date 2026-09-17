from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.language.enums import LanguageLevel


language_level_enum = Enum(
    LanguageLevel,
    name="language_level",
    create_constraint=False,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class LanguageReadingV2StudentState(Base):
    __tablename__ = "language_reading_v2_student_state"
    __table_args__ = (
        UniqueConstraint("student_id", "language_id", name="uq_language_reading_v2_student_state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    current_cefr: Mapped[LanguageLevel] = mapped_column(language_level_enum, default=LanguageLevel.A1)
    current_stage: Mapped[str] = mapped_column(String(24), default="Beginner")
    status: Mapped[str] = mapped_column(String(24), default="active")
    unlocked_rank: Mapped[int] = mapped_column(Integer, default=0)
    readiness_target_level: Mapped[LanguageLevel | None] = mapped_column(language_level_enum, nullable=True)
    recent_mastery_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LanguageReadingV2StageProgress(Base):
    __tablename__ = "language_reading_v2_stage_progress"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "language_id",
            "cefr_level",
            "internal_stage",
            name="uq_language_reading_v2_stage_progress",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    cefr_level: Mapped[LanguageLevel] = mapped_column(language_level_enum, index=True)
    internal_stage: Mapped[str] = mapped_column(String(24), index=True)
    status: Mapped[str] = mapped_column(String(24), default="locked")
    attempts_completed: Mapped[int] = mapped_column(Integer, default=0)
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)
    subskill_mastery_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    question_type_mastery_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    recent_attempt_ids_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    mastered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LanguageReadingV2Attempt(Base):
    __tablename__ = "language_reading_v2_attempts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    cefr_level: Mapped[LanguageLevel] = mapped_column(language_level_enum, index=True)
    internal_stage: Mapped[str] = mapped_column(String(24), index=True)
    mode: Mapped[str] = mapped_column(String(16), default="practice", index=True)
    status: Mapped[str] = mapped_column(String(32), default="ready", index=True)
    target_next_cefr: Mapped[LanguageLevel | None] = mapped_column(language_level_enum, nullable=True)
    generation_blueprint_json: Mapped[dict] = mapped_column(JSONB)
    generated_activity_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validation_result_json: Mapped[dict] = mapped_column(JSONB)
    model_used: Mapped[str] = mapped_column(String(80), default="local_mock")
    prompt_version: Mapped[str] = mapped_column(String(80), default="reading_v2_r1")
    validator_version: Mapped[str] = mapped_column(String(80), default="reading_v2_validator_r1")
    score_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    question_results_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
