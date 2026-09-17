"""Speaking promotion readiness engine + persistence (S17).

Never writes official_speaking_cefr or learning_stage_speaking.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.services.language_progression_service import ensure_progression_row, get_official_cefr
from app.services.language_speaking.enums import SpeakingLearningStage
from app.services.language_speaking_knowledge_model.locking import lock_speaking_progression_row
from app.services.language_speaking_learning_stage.service import build_speaking_stage_signal_snapshot
from app.services.language_speaking_promotion_readiness.scoring import (
    apply_dual_gate_unlock,
    evaluate_speaking_promotion_readiness,
)
from app.services.language_speaking_promotion_readiness.storage import (
    merge_speaking_promotion_into_payload,
    speaking_promotion_bucket_from_payload,
)
from app.services.language_speaking_promotion_readiness.types import SpeakingPromotionReadinessResult


def _read_stage(row) -> SpeakingLearningStage:
    raw = getattr(row, "learning_stage_speaking", None)
    try:
        return SpeakingLearningStage(max(1, min(3, int(raw or 1))))
    except (TypeError, ValueError):
        return SpeakingLearningStage.foundation


async def evaluate_and_persist_speaking_promotion_readiness(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
    official_cefr: str | None = None,
    stability_requirements_passed: bool = False,
) -> SpeakingPromotionReadinessResult:
    """Evaluate readiness from fresh S15 snapshot and persist score + projection."""
    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    row = await lock_speaking_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        from app.services.language_speaking_learning_stage.signals import gather_speaking_stage_signals

        snap = gather_speaking_stage_signals(
            official_cefr=(official_cefr or "A2").upper(),
            current_stage=SpeakingLearningStage.foundation,
            knowledge_model=None,
            refresh_retention=False,
        )
        result = evaluate_speaking_promotion_readiness(snap)
        return apply_dual_gate_unlock(result, stability_requirements_passed=False)

    if official_cefr is None:
        official = await get_official_cefr(
            db, student_id=student_id, language_id=language_id, skill="speaking"
        )
        official_cefr = official.level.value if hasattr(official, "level") else str(official)
    official_cefr = str(official_cefr).upper()

    snapshot = await build_speaking_stage_signal_snapshot(
        db,
        student_id=student_id,
        language_id=language_id,
        official_cefr=official_cefr,
    )
    # Guard: snapshot CEFR must match evaluation CEFR
    if snapshot.official_cefr.upper() != official_cefr:
        from app.services.language_speaking_promotion_readiness.types import (
            SpeakingReadinessStatus,
            SpeakingUnlockState,
            finalize_readiness_fingerprint,
        )
        from app.services.language_speaking_promotion_readiness.policy import (
            READINESS_POLICY_VERSION,
            READINESS_SCHEMA_VERSION,
        )

        return finalize_readiness_fingerprint(
            SpeakingPromotionReadinessResult(
                schema_version=READINESS_SCHEMA_VERSION,
                policy_version=READINESS_POLICY_VERSION,
                official_cefr=official_cefr,
                target_cefr=None,
                current_stage=_read_stage(row),
                eligible_for_readiness=False,
                readiness_score=0,
                status=SpeakingReadinessStatus.blocked,
                hard_blockers=("stale_cefr",),
                advisory_signals=(),
                unknown_signals=(),
                dimensions=(),
                source_stage_signal_fingerprint=snapshot.snapshot_fingerprint,
                snapshot_fingerprint="",
                estimated_remaining=100.0,
                hard_blockers_empty=False,
                score_meets_promotion_floor=False,
                stability_requirements_passed=False,
                spa_unlocked=False,
                unlock_state=SpeakingUnlockState.locked,
                strengths=(),
                next_actions=("Refresh progression state and try again.",),
            )
        )

    result = evaluate_speaking_promotion_readiness(snapshot)
    result = apply_dual_gate_unlock(
        result, stability_requirements_passed=stability_requirements_passed
    )

    payload = dict(row.promotion_readiness_json or {})
    bucket = speaking_promotion_bucket_from_payload(payload)
    bucket["readiness"] = result.to_internal_dict()
    bucket["student_projection"] = result.to_student_safe_dict()
    payload = merge_speaking_promotion_into_payload(payload, bucket)
    row.promotion_readiness_json = payload
    row.promotion_readiness_score = int(result.readiness_score)
    flag_modified(row, "promotion_readiness_json")
    await db.flush()
    return result
