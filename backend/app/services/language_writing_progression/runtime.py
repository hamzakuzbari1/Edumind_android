"""Writing progression pipeline — stage → readiness → stability after lesson complete."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_progression_service import ensure_progression_row
from app.services.language_writing_learning_stage import evaluate_and_persist_writing_stage
from app.services.language_writing_promotion_readiness import evaluate_and_persist_writing_promotion_readiness
from app.services.language_writing_promotion_stability import evaluate_and_persist_writing_promotion_stability


async def run_writing_progression_engines(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> None:
    """Execute writing progression engines after lesson completion."""
    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    await evaluate_and_persist_writing_stage(db, student_id=student_id, language_id=language_id)
    await evaluate_and_persist_writing_promotion_readiness(db, student_id=student_id, language_id=language_id)
    await evaluate_and_persist_writing_promotion_stability(db, student_id=student_id, language_id=language_id)
