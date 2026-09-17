"""Official promotion event helpers (Phase 5.5)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_progression_service import record_progression_event


async def record_official_listening_promotion_event(
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
        event_type="listening_official_promotion_applied",
        payload_json=payload_json,
        force=True,
    )
    return event.id if event is not None else None
