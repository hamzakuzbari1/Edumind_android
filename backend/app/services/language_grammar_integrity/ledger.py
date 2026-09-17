"""Append-only grammar evidence ledger + durable replay protection (Wave D)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.grammar_integrity import GrammarEvidenceLedger
from app.services.language_grammar_integrity.curriculum_version import get_curriculum_version
from app.services.language_grammar_integrity.errors import GrammarIntegrityError


LedgerInsertResult = Literal["inserted", "duplicate"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def try_append_evidence(
    db: AsyncSession,
    *,
    observation_id: str,
    student_id: int,
    language_id: int,
    grammar_id: str,
    skill: str,
    score: float,
    confidence: float,
    activity_session_id: uuid.UUID | None,
    lesson_id: str = "",
    activity_type: str = "",
    curriculum_version: str | None = None,
    observed_at: datetime | None = None,
) -> LedgerInsertResult:
    """Append evidence under a savepoint. Duplicates never update historical rows."""
    oid = (observation_id or "").strip()
    if not oid:
        raise GrammarIntegrityError("missing_observation_id", "observation_id is required")
    row = GrammarEvidenceLedger(
        id=uuid.uuid4(),
        observation_id=oid,
        student_id=int(student_id),
        language_id=int(language_id),
        grammar_id=str(grammar_id).strip().lower(),
        activity_session_id=activity_session_id,
        lesson_id=str(lesson_id or ""),
        activity_type=str(activity_type or ""),
        skill=str(skill or "").strip().lower(),
        score=max(0.0, min(100.0, float(score))),
        confidence=max(0.0, min(1.0, float(confidence))),
        curriculum_version=(curriculum_version or get_curriculum_version()),
        observed_at=observed_at or _utcnow(),
        created_at=_utcnow(),
    )
    try:
        async with db.begin_nested():
            db.add(row)
            await db.flush()
        return "inserted"
    except IntegrityError:
        return "duplicate"


async def append_evidence_or_raise(db: AsyncSession, **kwargs) -> None:
    """Append evidence; raise on duplicate (strict path)."""
    result = await try_append_evidence(db, **kwargs)
    if result == "duplicate":
        raise GrammarIntegrityError(
            "duplicate_observation",
            f"Observation already recorded: {kwargs.get('observation_id')}",
        )
