from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.language.enums import LanguageLevel, LanguageSkill, OverallLevelMethod


class LanguageAssessment(Base):
    __tablename__ = "language_assessments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("language_placement_attempts.id", ondelete="CASCADE"), unique=True)
    overall_level: Mapped[LanguageLevel | None] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    overall_calculation_method: Mapped[str] = mapped_column(String(32), default=OverallLevelMethod.bottleneck.value)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    skill_scores: Mapped[list["LanguageAssessmentSkillScore"]] = relationship(back_populates="assessment")


class LanguageAssessmentSkillScore(Base):
    __tablename__ = "language_assessment_skill_scores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("language_assessments.id", ondelete="CASCADE"), index=True)
    skill: Mapped[LanguageSkill] = mapped_column(
        Enum(LanguageSkill, name="language_skill", create_constraint=False, values_callable=lambda e: [x.value for x in e])
    )
    score_percent: Mapped[float] = mapped_column(Float, default=0)
    level: Mapped[LanguageLevel] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e])
    )
    raw_metrics_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_evaluation_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    assessment: Mapped["LanguageAssessment"] = relationship(back_populates="skill_scores")
