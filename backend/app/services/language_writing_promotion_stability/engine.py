"""Writing promotion stability — rolling readiness history."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.services.language_progression_service import ensure_progression_row
from app.services.language_writing_promotion_readiness import evaluate_writing_promotion_readiness


@dataclass(frozen=True, slots=True)
class WritingPromotionStabilityResult:
    promotion_confidence: int
    readiness_stability: float
    prediction: str
    history_length: int


async def evaluate_writing_promotion_stability(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> WritingPromotionStabilityResult:
    readiness = await evaluate_writing_promotion_readiness(db, student_id=student_id, language_id=language_id)
    row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    payload = dict(row.promotion_readiness_json or {}) if row else {}
    bucket = payload.get("writing_stability") or {}
    history: list[float] = list(bucket.get("readiness_history") or [])
    history.append(float(readiness.readiness_score))
    history = history[-10:]
    if len(history) >= 3:
        m = mean(history)
        var = sum((x - m) ** 2 for x in history) / len(history)
        stability = max(0.0, min(1.0, 1.0 - var / 400.0))
    else:
        stability = 0.5
    confidence = int(round(max(0.0, min(1.0, (readiness.readiness_score / 100.0) * 0.7 + stability * 0.3)) * 100))
    if readiness.readiness_score >= 100:
        prediction = "Promotion Available"
    elif readiness.readiness_score >= 80:
        prediction = "Very Likely"
    elif readiness.readiness_score >= 50:
        prediction = "Building"
    else:
        prediction = "Not Ready"
    bucket["readiness_history"] = history
    bucket["promotion_confidence"] = confidence
    bucket["readiness_stability"] = round(stability, 4)
    bucket["prediction"] = prediction
    payload["writing_stability"] = bucket
    if row is not None:
        row.promotion_readiness_json = payload
        flag_modified(row, "promotion_readiness_json")
        await db.flush()
    return WritingPromotionStabilityResult(
        promotion_confidence=confidence,
        readiness_stability=stability,
        prediction=prediction,
        history_length=len(history),
    )


async def evaluate_and_persist_writing_promotion_stability(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> WritingPromotionStabilityResult:
    return await evaluate_writing_promotion_stability(db, student_id=student_id, language_id=language_id)
