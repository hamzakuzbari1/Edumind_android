"""Load active speaking session EVI overlay from JSONB (S9)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.progression import LanguageProgression
from app.services.language_progression_service import ensure_progression_row
from app.services.language_speaking_knowledge_model.storage import speaking_bucket_from_payload
from app.services.language_speaking_lesson_planner.storage import load_s9_state


async def load_session_evi_overlay(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
) -> dict[str, object] | None:
    row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    bucket = speaking_bucket_from_payload(dict(row.promotion_readiness_json or {}))
    state = load_s9_state(bucket)
    blueprint, session = state.blueprint, state.session
    if blueprint is None:
        return None
    ctx: dict[str, Any] = dict(blueprint.alex_context.to_dict())
    if session is not None:
        ctx["phase"] = session.phase.value
    return ctx
