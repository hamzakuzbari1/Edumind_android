"""Deterministic listening lesson selection from eligible pool (Phase 2.2)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.content import LanguageContentItem
from app.services.language_listening_confidence import load_student_confidence
from app.services.language_listening_selection.ranker import select_best_candidate


async def list_eligible_unseen_candidates(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    level: str,
    pool_filters_fn,
    completed_ids_subquery,
) -> list[LanguageContentItem]:
    rows = (
        await db.execute(
            select(LanguageContentItem)
            .where(
                *pool_filters_fn(
                    student_id=student_id, language_id=language_id, level=level, active_only=True
                ),
                LanguageContentItem.id.notin_(completed_ids_subquery(student_id)),
            )
            .order_by(LanguageContentItem.sort_order.asc(), LanguageContentItem.id.asc())
        )
    ).scalars().all()
    return list(rows)


async def select_deterministic_listening_lesson(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    level: str,
    pool_filters_fn,
    completed_ids_subquery,
) -> LanguageContentItem | None:
    candidates = await list_eligible_unseen_candidates(
        db,
        student_id=student_id,
        language_id=language_id,
        level=level,
        pool_filters_fn=pool_filters_fn,
        completed_ids_subquery=completed_ids_subquery,
    )
    if not candidates:
        return None

    confidence = await load_student_confidence(
        db, student_id=student_id, language_id=language_id, level=level
    )
    return select_best_candidate(candidates, confidence=confidence)
