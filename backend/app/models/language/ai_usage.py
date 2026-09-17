"""Phase 12 — AI token-usage ledger (cost/volume telemetry).

One row per Gemini JSON call, written best-effort from a dedicated session inside the wrapper (so no
session threading through callers). Generic columns; integer auto id.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LanguageAiUsage(Base):
    __tablename__ = "language_ai_usage"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    operation: Mapped[str] = mapped_column(String(100), default="", server_default="")
    model: Mapped[str] = mapped_column(String(80), default="", server_default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
