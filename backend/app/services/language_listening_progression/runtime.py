"""Wire Phase 5 listening progression engines into the lesson submit runtime (PR-1).

Reuses existing engines only — no duplicated scoring or gate logic.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_learning_stage import evaluate_and_persist_listening_stage
from app.services.language_progression_service import ensure_progression_row
from app.services.language_promotion_readiness import evaluate_and_persist_listening_promotion_readiness
from app.services.language_promotion_stability import evaluate_and_persist_listening_promotion_stability


async def run_listening_progression_after_submit(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> None:
    """Execute the listening progression pipeline after confidence/challenge updates."""
    await ensure_progression_row(db, student_id=student_id, language_id=language_id)

    await evaluate_and_persist_listening_stage(
        db,
        student_id=student_id,
        language_id=language_id,
    )
    await evaluate_and_persist_listening_promotion_readiness(
        db,
        student_id=student_id,
        language_id=language_id,
    )
    await evaluate_and_persist_listening_promotion_stability(
        db,
        student_id=student_id,
        language_id=language_id,
    )
