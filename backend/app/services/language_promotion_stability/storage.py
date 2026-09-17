"""Promotion stability persistence (Phase 5.3.1).

Persists promotion_confidence, readiness_stability, and history inside
promotion_readiness_json — never Official CEFR columns.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.progression import LanguageProgression
from app.services.language_listening_progression.json_mutation import mutate_listening_progression_json
from app.services.language_progression_service import record_progression_event
from app.services.language_promotion_stability.types import PromotionStabilityResult, ReadinessHistoryEntry


async def load_readiness_history(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> list[ReadinessHistoryEntry]:
    row = await db.get(LanguageProgression, {"student_id": student_id, "language_id": language_id})
    if row is None or not row.promotion_readiness_json:
        return []
    stability = row.promotion_readiness_json.get("stability") or {}
    raw = stability.get("history") or []
    return [ReadinessHistoryEntry.from_dict(item) for item in raw if isinstance(item, dict)]


async def save_listening_promotion_stability(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    result: PromotionStabilityResult,
    history: list[ReadinessHistoryEntry],
) -> LanguageProgression | None:
    def mutator(payload: dict) -> None:
        payload["stability"] = {
            "skill": "listening",
            "promotion_confidence": result.promotion_confidence,
            "readiness_stability": result.readiness_stability,
            "rolling_average": result.rolling_average,
            "rolling_minimum": result.rolling_minimum,
            "rolling_variance": result.rolling_variance,
            "stable_lessons": result.stable_lessons,
            "current_streak": result.current_streak,
            "best_streak": result.best_streak,
            "last_readiness_scores": list(result.last_readiness_scores),
            "smoothed_readiness": result.telemetry.smoothed_readiness,
            "prediction": result.prediction.value,
            "recommendation": result.recommendation,
            "recommendations": list(result.recommendations),
            "history": [entry.to_dict() for entry in history],
        }

    row, _ = await mutate_listening_progression_json(
        db,
        student_id=student_id,
        language_id=language_id,
        mutator=mutator,
    )
    if row is None:
        return None

    await record_progression_event(
        db,
        student_id=student_id,
        language_id=language_id,
        event_type="listening_promotion_stability_updated",
        payload_json={
            "promotion_confidence": result.promotion_confidence,
            "readiness_stability": result.readiness_stability,
            "prediction": result.prediction.value,
            "official_cefr": result.official_cefr,
        },
        force=True,
    )
    return row
