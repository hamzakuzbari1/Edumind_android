"""Progression events for speaking official promotion (S20)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_progression_service import record_progression_event


async def record_official_speaking_promotion_event(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    payload_json: dict[str, Any],
) -> int | None:
    event = await record_progression_event(
        db,
        student_id=student_id,
        language_id=language_id,
        event_type="speaking_official_promotion_applied",
        payload_json=payload_json,
        force=True,
    )
    return getattr(event, "id", None) if event is not None else None
