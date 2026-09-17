from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.language.enums import LanguageLevel, LanguageSkill


class LanguageContentItem(Base):
    __tablename__ = "language_content_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    skill: Mapped[LanguageSkill] = mapped_column(
        Enum(LanguageSkill, name="language_skill", create_constraint=False, values_callable=lambda e: [x.value for x in e])
    )
    level: Mapped[LanguageLevel] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e])
    )
    content_type: Mapped[str] = mapped_column(String(32), default="lesson")
    title: Mapped[str] = mapped_column(String(500))
    body_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    media_object_id: Mapped[int | None] = mapped_column(ForeignKey("media_objects.id", ondelete="SET NULL"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
