"""Speaking progression orchestration runtime (S16 + S17).

Orchestrates stage transition then promotion readiness/stability.
Does NOT write learning_stage_speaking or official_speaking_cefr directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.services.language_progression_service import ensure_progression_row
from app.services.language_speaking_knowledge_model.locking import lock_speaking_progression_row
from app.services.language_speaking_learning_stage.stage_runtime import (
    SpeakingStagePersistResult,
    evaluate_and_persist_speaking_stage,
)
from app.services.language_speaking_promotion_readiness.engine import (
    evaluate_and_persist_speaking_promotion_readiness,
)
from app.services.language_speaking_promotion_readiness.scoring import apply_dual_gate_unlock
from app.services.language_speaking_promotion_readiness.storage import (
    merge_speaking_promotion_into_payload,
    speaking_promotion_bucket_from_payload,
)
from app.services.language_speaking_promotion_readiness.types import SpeakingPromotionReadinessResult
from app.services.language_speaking_promotion_stability.engine import (
    evaluate_and_persist_speaking_promotion_stability,
)
from app.services.language_speaking_promotion_stability.types import SpeakingPromotionStabilityResult


@dataclass(frozen=True, slots=True)
class SpeakingProgressionEnginesResult:
    stage: SpeakingStagePersistResult
    readiness: SpeakingPromotionReadinessResult
    stability: SpeakingPromotionStabilityResult


async def run_speaking_progression_engines(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
) -> SpeakingProgressionEnginesResult:
    """Post-session progression: S16 stage gate → S17 readiness → S17 stability dual-gate."""
    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    stage = await evaluate_and_persist_speaking_stage(
        db, student_id=student_id, language_id=language_id
    )
    readiness = await evaluate_and_persist_speaking_promotion_readiness(
        db,
        student_id=student_id,
        language_id=language_id,
        stability_requirements_passed=False,
    )
    stability = await evaluate_and_persist_speaking_promotion_stability(
        db,
        student_id=student_id,
        language_id=language_id,
        readiness=readiness,
    )
    # Dual-gate finalize: empty hard blockers AND score floor AND independent stability pass.
    readiness = apply_dual_gate_unlock(
        readiness, stability_requirements_passed=stability.requirements_passed
    )
    row = await lock_speaking_progression_row(db, student_id=student_id, language_id=language_id)
    if row is not None:
        payload = dict(row.promotion_readiness_json or {})
        bucket = speaking_promotion_bucket_from_payload(payload)
        bucket["readiness"] = readiness.to_internal_dict()
        bucket["student_projection"] = readiness.to_student_safe_dict()
        bucket["stability"] = stability.to_dict()
        payload = merge_speaking_promotion_into_payload(payload, bucket)
        row.promotion_readiness_json = payload
        row.promotion_readiness_score = int(readiness.readiness_score)
        flag_modified(row, "promotion_readiness_json")
        await db.flush()

    return SpeakingProgressionEnginesResult(
        stage=stage,
        readiness=readiness,
        stability=stability,
    )
