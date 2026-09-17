"""Read-only DB orchestration for Speaking stage signal snapshots (S15).

NEVER writes:
- learning_stage_speaking
- official_speaking_cefr
- promotion readiness
- S2 mastery / knowledge model
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_progression_service import ensure_progression_row, get_official_cefr
from app.services.language_speaking.enums import SpeakingLearningStage
from app.services.language_speaking_knowledge_model.storage import (
    knowledge_model_from_speaking_bucket,
    speaking_bucket_from_payload,
)
from app.services.language_speaking_learning_stage.signals import gather_speaking_stage_signals
from app.services.language_speaking_learning_stage.types import SpeakingStageSignalSnapshot
from app.services.language_speaking_lesson_planner.storage import load_s9_state


def _read_current_stage(row) -> SpeakingLearningStage:
    raw = getattr(row, "learning_stage_speaking", None)
    try:
        return SpeakingLearningStage(max(1, min(3, int(raw or 1))))
    except (TypeError, ValueError):
        return SpeakingLearningStage.foundation


async def build_speaking_stage_signal_snapshot(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
    official_cefr: str | None = None,
) -> SpeakingStageSignalSnapshot:
    """Load authoritative state and project a stage-signal snapshot (read-only)."""
    row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    if official_cefr is None:
        official = await get_official_cefr(
            db, student_id=student_id, language_id=language_id, skill="speaking"
        )
        official_cefr = official.level.value if hasattr(official, "level") else str(official)

    payload = dict(row.promotion_readiness_json or {}) if row is not None else {}
    bucket = speaking_bucket_from_payload(payload)
    knowledge_model = knowledge_model_from_speaking_bucket(
        bucket, student_id=student_id, language_id=language_id
    )
    state = load_s9_state(bucket)
    lineage = state.attempt_lineage
    current_stage = _read_current_stage(row) if row is not None else SpeakingLearningStage.foundation

    return gather_speaking_stage_signals(
        official_cefr=str(official_cefr),
        current_stage=current_stage,
        knowledge_model=knowledge_model,
        attempt_lineage=lineage,
    )
