"""Two-factor authentication challenges and user settings."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TwoFactorMethod(str, enum.Enum):
    email = "email"
    totp = "totp"


class TwoFactorPurpose(str, enum.Enum):
    login = "login"
    enable = "enable"
    disable = "disable"


class TwoFactorChallenge(Base):
    __tablename__ = "two_factor_challenges"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(16), index=True)
    challenge_token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    resend_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
