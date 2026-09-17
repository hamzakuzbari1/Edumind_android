"""API orchestration for Listening Official Promotion — reuses Phase 5.5 engine only."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.progression import LanguageProgression
from app.schemas.language_official_promotion import (
    JourneyResetOut,
    ListeningOfficialPromotionOut,
    OfficialPromotionTelemetryOut,
)
from app.services.language_listening_progression.locking import lock_listening_progression_row
from app.services.language_official_promotion import apply_listening_official_promotion
from app.services.language_progression_service import PROGRESSION_UNAVAILABLE_REASON, ensure_progression_row
from app.services.language_official_promotion.storage import (
    get_latest_promotion_test_attempt,
    is_session_already_promoted,
    resolve_recommended_next_listening_lesson,
)
from app.services.language_official_promotion.types import PromotionAppliedResult


class OfficialPromotionApiError(Exception):
    """Maps engine outcomes to HTTP status codes without modifying the engine."""

    def __init__(self, status_code: int, detail: dict | str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(str(detail))


def _result_to_out(
    result: PromotionAppliedResult,
    *,
    recommended_next_lesson: str | None,
) -> ListeningOfficialPromotionOut:
    journey = result.journey_reset
    telemetry = result.telemetry
    return ListeningOfficialPromotionOut(
        promotion_success=result.promotion_success,
        old_cefr=result.old_cefr,
        new_cefr=result.new_cefr,
        new_learning_stage=result.new_learning_stage,
        journey_reset=JourneyResetOut(
            learning_stage=journey.learning_stage,
            learning_stage_name=journey.learning_stage_name,
            promotion_readiness_score=journey.promotion_readiness_score,
            promotion_confidence=journey.promotion_confidence,
            transition_gate_reset=journey.transition_gate_reset,
            promotion_test_session_closed=journey.promotion_test_session_closed,
            preserved_exam_history=journey.preserved_exam_history,
            preserved_stability_history=journey.preserved_stability_history,
            preserved_promotion_history=journey.preserved_promotion_history,
        ),
        summary=result.summary,
        recommended_next_lesson=recommended_next_lesson,
        telemetry=OfficialPromotionTelemetryOut(
            old_cefr=telemetry.old_cefr,
            new_cefr=telemetry.new_cefr,
            promotion_test_session_id=telemetry.promotion_test_session_id,
            promotion_test_score=telemetry.promotion_test_score,
            promotion_test_attempt_number=telemetry.promotion_test_attempt_number,
            promotion_reason=telemetry.promotion_reason,
            promoted_at=telemetry.promoted_at,
            overall_cefr_updated=telemetry.overall_cefr_updated,
            previous_overall_cefr=telemetry.previous_overall_cefr,
            new_overall_cefr=telemetry.new_overall_cefr,
        ),
        event_id=result.event_id,
        reason=result.denial_reason,
    )


def _denial_status_code(result: PromotionAppliedResult) -> int:
    reason = (result.denial_reason or "").lower()
    if "no promotion test attempt found" in reason:
        return 404
    if "no progression row found" in reason:
        return 404
    return 409


async def apply_listening_official_promotion_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> ListeningOfficialPromotionOut:
    """Apply official promotion via the engine and map the result to API semantics."""
    if await ensure_progression_row(db, student_id=student_id, language_id=language_id) is None:
        raise OfficialPromotionApiError(
            503,
            {
                "promotion_success": False,
                "reason": PROGRESSION_UNAVAILABLE_REASON,
                "progression_available": False,
            },
        )

    row = await lock_listening_progression_row(
        db, student_id=student_id, language_id=language_id
    )
    if row is None:
        raise OfficialPromotionApiError(
            404,
            {
                "promotion_success": False,
                "reason": "No progression row found.",
            },
        )

    payload = dict(row.promotion_readiness_json or {})
    attempt = get_latest_promotion_test_attempt(payload)
    already_promoted = (
        attempt is not None and is_session_already_promoted(payload, attempt.session_id)
    )

    result = await apply_listening_official_promotion(
        db,
        student_id=student_id,
        language_id=language_id,
        locked_row=row,
    )

    if not result.promotion_success:
        raise OfficialPromotionApiError(
            _denial_status_code(result),
            {
                "promotion_success": False,
                "reason": result.denial_reason or "Promotion denied.",
                "old_cefr": result.old_cefr,
                "new_cefr": result.new_cefr,
            },
        )

    lesson = await resolve_recommended_next_listening_lesson(
        db,
        student_id=student_id,
        language_id=language_id,
        level=result.new_cefr,
    )
    response = _result_to_out(result, recommended_next_lesson=lesson)

    if already_promoted:
        raise OfficialPromotionApiError(409, response.model_dump())

    return response
