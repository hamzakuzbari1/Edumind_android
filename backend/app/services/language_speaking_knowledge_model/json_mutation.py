"""Atomic mutation of speaking knowledge model inside promotion_readiness_json."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.progression import LanguageProgression
from app.services.language_progression_service import ensure_progression_row
from app.services.language_speaking_knowledge_model.locking import lock_speaking_progression_row
from app.services.language_speaking_knowledge_model.storage import (
    SPEAKING_BUCKET_KEY,
    knowledge_model_from_speaking_bucket,
    merge_knowledge_model_into_speaking_bucket,
    speaking_bucket_from_payload,
)

MutatorResult = TypeVar("MutatorResult")


async def mutate_speaking_knowledge_model(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    mutator: Callable[[object], MutatorResult],
    locked_row: LanguageProgression | None = None,
) -> tuple[LanguageProgression | None, MutatorResult | None]:
    """Mutate knowledge model while preserving unrelated promotion_readiness_json keys."""
    row = locked_row
    if row is None:
        row = await lock_speaking_progression_row(
            db, student_id=student_id, language_id=language_id
        )
    if row is None:
        row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        return None, None

    payload = dict(row.promotion_readiness_json or {})
    speaking_bucket = speaking_bucket_from_payload(payload)
    model = knowledge_model_from_speaking_bucket(
        speaking_bucket, student_id=student_id, language_id=language_id
    )
    result = mutator(model)
    speaking_bucket = merge_knowledge_model_into_speaking_bucket(speaking_bucket, model)
    payload[SPEAKING_BUCKET_KEY] = speaking_bucket
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")
    await db.flush()
    return row, result
