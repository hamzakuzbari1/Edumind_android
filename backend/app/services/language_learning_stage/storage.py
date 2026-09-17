"""Learning stage persistence on language_progression (Phase 5.1).

Only touches learning_stage_listening — never Official CEFR columns.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.progression import LanguageProgression
from app.services.language_progression_service import record_progression_event


async def load_listening_stage(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> int:
    """Return stored listening learning stage (1–3), default 1."""
    row = await db.get(LanguageProgression, {"student_id": student_id, "language_id": language_id})
    if row is None:
        return 1
    return max(1, min(3, int(row.learning_stage_listening or 1)))


async def save_listening_stage(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    stage: int,
    official_cefr: str,
    stage_score: int,
    previous_stage: int,
    force: bool = False,
) -> LanguageProgression | None:
    """Persist listening learning stage only — Official CEFR columns are never modified."""
    stage = max(1, min(3, int(stage)))
    row = await db.get(LanguageProgression, {"student_id": student_id, "language_id": language_id})
    if row is None:
        return None

    prev = int(row.learning_stage_listening or 1)
    if prev == stage and not force:
        return row

    row.learning_stage_listening = stage
    await db.flush()

    await record_progression_event(
        db,
        student_id=student_id,
        language_id=language_id,
        event_type="listening_learning_stage_changed",
        payload_json={
            "official_cefr": official_cefr,
            "previous_stage": previous_stage,
            "new_stage": stage,
            "stage_score": stage_score,
        },
        force=True,
    )
    return row
