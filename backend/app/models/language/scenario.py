"""Role-play scenarios for the speaking conversation feature."""

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.language.enums import LanguageLevel


class LanguageConversationScenario(Base):
    __tablename__ = "language_conversation_scenarios"
    __table_args__ = (
        UniqueConstraint("language_id", "scenario_key", name="uq_lang_conversation_scenario_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    scenario_key: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(32), default="daily_conversation", server_default="daily_conversation")
    title_en: Mapped[str] = mapped_column(String(200))
    title_ar: Mapped[str] = mapped_column(String(200))
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    level_min: Mapped[LanguageLevel] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e])
    )
    ai_role: Mapped[str] = mapped_column(String(200))
    student_role: Mapped[str] = mapped_column(String(200))
    opening_line: Mapped[str] = mapped_column(Text)
    target_skills_json: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
