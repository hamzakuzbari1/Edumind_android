"""Canonical atomic mutation path for promotion_readiness_json (STAB-3)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.progression import LanguageProgression
from app.services.language_listening_progression.locking import lock_listening_progression_row

MutatorResult = TypeVar("MutatorResult")


async def mutate_listening_progression_json(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    mutator: Callable[[dict], MutatorResult],
    locked_row: LanguageProgression | None = None,
) -> tuple[LanguageProgression | None, MutatorResult | None]:
    """Acquire FOR UPDATE, mutate a copy of promotion_readiness_json, persist atomically."""
    row = locked_row
    if row is None:
        row = await lock_listening_progression_row(
            db, student_id=student_id, language_id=language_id
        )
    if row is None:
        return None, None

    payload = dict(row.promotion_readiness_json or {})
    result = mutator(payload)
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")
    await db.flush()
    return row, result
