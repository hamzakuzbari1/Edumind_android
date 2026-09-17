"""Atomic mutation of writing bucket inside promotion_readiness_json."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.progression import LanguageProgression
from app.services.language_progression_service import ensure_progression_row
from app.services.language_writing_progression.storage import WRITING_PROGRESSION_KEY, writing_state_from_payload

MutatorResult = TypeVar("MutatorResult")


async def mutate_writing_progression_json(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    mutator: Callable[[dict], MutatorResult],
) -> tuple[LanguageProgression | None, MutatorResult | None]:
    row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        return None, None
    payload = dict(row.promotion_readiness_json or {})
    writing = writing_state_from_payload(payload)
    result = mutator(writing)
    payload[WRITING_PROGRESSION_KEY] = writing
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")
    await db.flush()
    return row, result
