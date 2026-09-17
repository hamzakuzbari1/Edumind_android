"""Per-scenario completion tracking for guided conversation scenarios."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LanguageScenarioProgress(Base):
    __tablename__ = "language_scenario_progress"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "language_id",
            "scenario_key",
            name="uq_language_scenario_progress_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    scenario_key: Mapped[str] = mapped_column(String(64))
    scenario_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="not_started", server_default="not_started")
    completion_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    best_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    best_scores_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    last_played_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
