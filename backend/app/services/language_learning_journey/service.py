"""Async Journey graph loader — readonly snapshots only."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_grammar_catalog.catalog import get_default_catalog
from app.services.language_grammar_mastery import get_grammar_mastery_snapshot
from app.services.language_grammar_progression import get_grammar_progression_snapshot
from app.services.language_learning_journey.flags import learning_journey_enabled
from app.services.language_learning_journey.projection import project_journey_graph
from app.services.language_learning_journey.types import JourneyGraph


async def build_learning_journey_graph(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
) -> JourneyGraph:
    catalog = get_default_catalog()
    if not learning_journey_enabled():
        return project_journey_graph(catalog=catalog, progression=None, mastery=None)

    progression = await get_grammar_progression_snapshot(
        db, student_id=student_id, language_id=language_id
    )
    mastery = await get_grammar_mastery_snapshot(
        db, student_id=student_id, language_id=language_id
    )
    return project_journey_graph(
        catalog=catalog,
        progression=progression,
        mastery=mastery,
    )
