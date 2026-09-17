"""Speaking promotion stability engine (S17).

Independent requirements gate for dual-gate SPA unlock.
Does not write official_speaking_cefr or learning_stage_speaking.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.services.language_progression_service import ensure_progression_row
from app.services.language_speaking_knowledge_model.locking import lock_speaking_progression_row
from app.services.language_speaking_promotion_readiness.storage import (
    merge_speaking_promotion_into_payload,
    speaking_promotion_bucket_from_payload,
)
from app.services.language_speaking_promotion_readiness.types import SpeakingPromotionReadinessResult
from app.services.language_speaking_promotion_stability.history import (
    append_history_entry,
    consecutive_high_scores,
    windowed,
)
from app.services.language_speaking_promotion_stability.policy import (
    DEFAULT_STABILITY_POLICY,
    SpeakingStabilityPolicy,
)
from app.services.language_speaking_promotion_stability.types import (
    LANGUAGE_SPEAKING_PROMOTION_STABILITY_SCHEMA,
    SpeakingPromotionStabilityResult,
    SpeakingReadinessHistoryEntry,
)


def evaluate_speaking_promotion_stability(
    readiness: SpeakingPromotionReadinessResult,
    history: list[SpeakingReadinessHistoryEntry],
    *,
    policy: SpeakingStabilityPolicy = DEFAULT_STABILITY_POLICY,
) -> tuple[SpeakingPromotionStabilityResult, list[SpeakingReadinessHistoryEntry]]:
    entry = SpeakingReadinessHistoryEntry(
        signal_fingerprint=readiness.source_stage_signal_fingerprint or readiness.snapshot_fingerprint,
        readiness_score=readiness.readiness_score,
        hard_blockers_empty=len(readiness.hard_blockers) == 0 and readiness.eligible_for_readiness,
        official_cefr=readiness.official_cefr,
        target_cefr=readiness.target_cefr,
    )
    # Only append when Advanced-eligible path has a fingerprint
    updated = list(history)
    if entry.signal_fingerprint:
        updated = append_history_entry(updated, entry, policy=policy)

    win = windowed(updated, policy=policy)
    scores = [e.readiness_score for e in win]
    if scores:
        avg = sum(scores) / len(scores)
        minimum = float(min(scores))
    else:
        avg = 0.0
        minimum = 0.0

    streak = consecutive_high_scores(updated, policy=policy)

    # Confidence: smoothed blend with anti-spike caps
    if len(updated) <= 1:
        confidence = min(float(readiness.readiness_score), policy.single_snapshot_confidence_cap)
    elif len(updated) < policy.min_history_for_pass:
        blended = 0.35 * readiness.readiness_score + 0.65 * avg
        confidence = min(blended, policy.short_history_confidence_cap)
    else:
        confidence = 0.45 * readiness.readiness_score + 0.55 * avg
        confidence = min(100.0, confidence)

    failed: list[str] = []
    if len(updated) < policy.min_history_for_pass:
        failed.append("insufficient_history")
    if streak < policy.min_consecutive_high_scores:
        failed.append("insufficient_consecutive_high_scores")
    if avg < policy.min_rolling_average:
        failed.append("low_rolling_average")
    if minimum < policy.min_rolling_minimum and len(scores) >= policy.min_history_for_pass:
        failed.append("low_rolling_minimum")
    if confidence < policy.min_promotion_confidence:
        failed.append("low_promotion_confidence")

    passed = len(failed) == 0
    result = SpeakingPromotionStabilityResult(
        schema_version=LANGUAGE_SPEAKING_PROMOTION_STABILITY_SCHEMA,
        policy_version=policy.policy_version,
        history_length=len(updated),
        rolling_average=round(avg, 1),
        rolling_minimum=round(minimum, 1),
        consecutive_high_scores=streak,
        promotion_confidence=round(confidence, 1),
        requirements_passed=passed,
        failed_requirements=tuple(failed),
        last_scores=tuple(scores),
    )
    return result, updated


async def evaluate_and_persist_speaking_promotion_stability(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    readiness: SpeakingPromotionReadinessResult,
    policy: SpeakingStabilityPolicy = DEFAULT_STABILITY_POLICY,
) -> SpeakingPromotionStabilityResult:
    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    row = await lock_speaking_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        result, _ = evaluate_speaking_promotion_stability(readiness, [], policy=policy)
        return result

    payload = dict(row.promotion_readiness_json or {})
    bucket = speaking_promotion_bucket_from_payload(payload)
    raw_hist = bucket.get("stability_history") or []
    history: list[SpeakingReadinessHistoryEntry] = []
    if isinstance(raw_hist, list):
        for item in raw_hist:
            if isinstance(item, dict):
                history.append(SpeakingReadinessHistoryEntry.from_dict(item))

    result, updated = evaluate_speaking_promotion_stability(readiness, history, policy=policy)
    bucket["stability_history"] = [e.to_dict() for e in updated]
    bucket["stability"] = result.to_dict()
    payload = merge_speaking_promotion_into_payload(payload, bucket)
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")
    await db.flush()
    return result
