"""Durable S13 Talk-with-Alex daily usage + live lease rows.

Cross-session / cross-day cost-control state — not educational progression.
Kept as dedicated relational tables (not promotion_readiness_json).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SpeakingLiveDailyUsage(Base):
    __tablename__ = "speaking_live_daily_usage"
    __table_args__ = (
        UniqueConstraint("student_id", "usage_date", name="uq_speaking_live_daily_usage_student_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    consumed_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False, default="s13.v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SpeakingLiveLease(Base):
    __tablename__ = "speaking_live_leases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accounted_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
