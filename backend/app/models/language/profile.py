from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.language.enums import LanguageLevel, LanguageOnboardingStep


class LanguageStudentProfile(Base):
    __tablename__ = "language_student_profiles"
    __table_args__ = (UniqueConstraint("student_id", "language_id", name="uq_language_student_profile"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    onboarding_step: Mapped[LanguageOnboardingStep] = mapped_column(
        Enum(LanguageOnboardingStep, name="language_onboarding_step", values_callable=lambda e: [x.value for x in e]),
        default=LanguageOnboardingStep.select_language,
    )
    selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    placement_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_assessment_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_allowed_retake_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    target_level: Mapped[LanguageLevel | None] = mapped_column(
        Enum(LanguageLevel, name="language_level", values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    certificate_level: Mapped[LanguageLevel | None] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    certificate_awarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_time_to_next_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_progress_percent: Mapped[int | None] = mapped_column(nullable=True)
    preferences_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    language: Mapped["Language"] = relationship()
