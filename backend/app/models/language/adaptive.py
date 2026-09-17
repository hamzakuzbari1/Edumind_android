"""Per-skill adaptive difficulty state — drives future promotion/demotion between CEFR levels."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.language.enums import LanguageLevel, LanguageSkill


class LanguageSkillLevelState(Base):
    __tablename__ = "language_skill_level_state"
    __table_args__ = (
        UniqueConstraint("student_id", "language_id", "skill", name="uq_language_skill_level_state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"))
    skill: Mapped[LanguageSkill] = mapped_column(
        Enum(LanguageSkill, name="language_skill", create_constraint=False, values_callable=lambda e: [x.value for x in e])
    )
    current_level: Mapped[LanguageLevel] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e])
    )
    consecutive_pass_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    consecutive_fail_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    recent_scores_json: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    last_level_change_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
