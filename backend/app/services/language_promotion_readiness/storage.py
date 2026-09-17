"""Promotion readiness persistence (Phase 5.3).

Only touches promotion_readiness_score / promotion_readiness_json — never Official CEFR.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.progression import LanguageProgression
from app.services.language_listening_progression.json_mutation import mutate_listening_progression_json
from app.services.language_progression_service import record_progression_event
from app.services.language_promotion_readiness.types import PromotionReadinessResult


def _readiness_fields_from_result(result: PromotionReadinessResult) -> dict:
    """Readiness-owned keys only — must not include nested buckets owned by other writers."""
    return {
        "skill": "listening",
        "official_cefr": result.official_cefr,
        "readiness_score": result.readiness_score,
        "status": result.status.value,
        "estimated_remaining": result.estimated_remaining,
        "primary_blockers": list(result.primary_blockers),
        "secondary_blockers": list(result.secondary_blockers),
        "strengths": list(result.strengths),
        "next_actions": list(result.next_actions),
        "persistent_stage": result.telemetry.persistent_stage,
        "stage_score": result.telemetry.stage_score,
        "gate_overall_score": result.telemetry.gate_overall_score,
        "gate_eligible": result.telemetry.gate_eligible,
        "dimensions": [
            {
                "name": d.name,
                "current": d.current,
                "required": d.required,
                "progress": d.progress,
                "contribution": d.contribution,
            }
            for d in result.telemetry.dimension_scores
        ],
    }


async def save_listening_promotion_readiness(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    result: PromotionReadinessResult,
) -> LanguageProgression | None:
    """Persist listening promotion readiness telemetry only."""

    def mutator(payload: dict) -> None:
        payload.update(_readiness_fields_from_result(result))

    row, _ = await mutate_listening_progression_json(
        db,
        student_id=student_id,
        language_id=language_id,
        mutator=mutator,
    )
    if row is None:
        return None

    row.promotion_readiness_score = result.readiness_score
    await db.flush()

    await record_progression_event(
        db,
        student_id=student_id,
        language_id=language_id,
        event_type="listening_promotion_readiness_updated",
        payload_json={
            "readiness_score": result.readiness_score,
            "status": result.status.value,
            "official_cefr": result.official_cefr,
        },
        force=True,
    )
    return row
