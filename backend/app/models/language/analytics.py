from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.language.enums import LanguageLevel


class LanguageAnalytics(Base):
    __tablename__ = "language_analytics"

    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), primary_key=True)
    reading_level: Mapped[LanguageLevel | None] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    listening_level: Mapped[LanguageLevel | None] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    writing_level: Mapped[LanguageLevel | None] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    speaking_level: Mapped[LanguageLevel | None] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    overall_level_internal: Mapped[LanguageLevel | None] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
        comment="Bottleneck level for path generation — not shown as sole headline in UI",
    )
    primary_focus_skill: Mapped[str | None] = mapped_column(String(32), nullable=True)
    strength_skill: Mapped[str | None] = mapped_column(String(32), nullable=True)
    vocabulary_count: Mapped[int] = mapped_column(Integer, default=0)
    estimated_time_to_next_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_progress_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    xp_keys_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    xp_total: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    level_xp: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    weekly_minutes_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    skill_growth_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    statistics_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
