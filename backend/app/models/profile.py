from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enrollment import OnboardingStep


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    interests_json: Mapped[str] = mapped_column(Text, default="[]")
    hobbies_json: Mapped[str] = mapped_column(Text, default="[]")
    difficulty: Mapped[str] = mapped_column(String(50), default="medium")
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    learning_style: Mapped[str] = mapped_column(String(32), default="theoretical")
    future_goal: Mapped[str] = mapped_column(String(32), default="undecided")
    preferred_explanation_style: Mapped[str] = mapped_column(String(32), default="normal")
    personality_mode: Mapped[str] = mapped_column(String(32), default="friendly_teacher")
    grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    onboarding_step: Mapped[OnboardingStep] = mapped_column(
        Enum(OnboardingStep), default=OnboardingStep.grade
    )
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parent_link_code: Mapped[str | None] = mapped_column(String(16), unique=True, nullable=True, index=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="profile")
