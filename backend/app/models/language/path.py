from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.language.enums import LanguageContentProgressStatus, LanguageLevel, LanguageSkill


class LanguageLearningPath(Base):
    __tablename__ = "language_learning_paths"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    assessment_id: Mapped[int | None] = mapped_column(
        ForeignKey("language_assessments.id", ondelete="SET NULL"), nullable=True
    )
    overall_level: Mapped[LanguageLevel | None] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    path_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LanguagePathItem(Base):
    __tablename__ = "language_path_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    path_id: Mapped[int] = mapped_column(ForeignKey("language_learning_paths.id", ondelete="CASCADE"), index=True)
    skill: Mapped[LanguageSkill] = mapped_column(
        Enum(LanguageSkill, name="language_skill", create_constraint=False, values_callable=lambda e: [x.value for x in e])
    )
    level: Mapped[LanguageLevel] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e])
    )
    content_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("language_content_items.id", ondelete="SET NULL"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[LanguageContentProgressStatus] = mapped_column(
        Enum(
            LanguageContentProgressStatus,
            name="language_content_progress_status",
            values_callable=lambda e: [x.value for x in e],
        ),
        default=LanguageContentProgressStatus.not_started,
    )
