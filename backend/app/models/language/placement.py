from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.language.enums import LanguagePlacementAttemptStatus, LanguageSkill


class LanguagePlacementSection(Base):
    __tablename__ = "language_placement_sections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    skill: Mapped[LanguageSkill] = mapped_column(
        Enum(LanguageSkill, name="language_skill", values_callable=lambda e: [x.value for x in e])
    )
    title_ar: Mapped[str] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class LanguagePlacementQuestion(Base):
    __tablename__ = "language_placement_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("language_placement_sections.id", ondelete="CASCADE"), index=True)
    question_type: Mapped[str] = mapped_column(String(32))
    prompt_json: Mapped[dict] = mapped_column(JSONB)
    media_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    answer_key_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    max_points: Mapped[int] = mapped_column(Integer, default=1)
    level_hint: Mapped[str | None] = mapped_column(String(8), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class LanguagePlacementAttempt(Base):
    __tablename__ = "language_placement_attempts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    status: Mapped[LanguagePlacementAttemptStatus] = mapped_column(
        Enum(
            LanguagePlacementAttemptStatus,
            name="language_placement_attempt_status",
            values_callable=lambda e: [x.value for x in e],
        ),
        default=LanguagePlacementAttemptStatus.in_progress,
    )
    is_retake: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LanguagePlacementResponse(Base):
    __tablename__ = "language_placement_responses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("language_placement_attempts.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("language_placement_questions.id", ondelete="CASCADE"), index=True
    )
    response_json: Mapped[dict] = mapped_column(JSONB)
    score: Mapped[float | None] = mapped_column(nullable=True)
    evaluation_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
