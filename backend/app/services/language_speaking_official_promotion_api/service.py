"""API orchestration for Speaking Official Promotion (S20)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.language_speaking_official_promotion import SpeakingOfficialPromotionOut
from app.services.language_progression_service import PROGRESSION_UNAVAILABLE_REASON, ensure_progression_row
from app.services.language_speaking_progression.locking import lock_speaking_progression_row
from app.services.language_speaking_official_promotion import apply_speaking_official_promotion
from app.services.language_speaking_official_promotion.storage import (
    is_assessment_already_promoted,
    is_attempt_already_promoted,
)
from app.services.language_speaking_official_promotion.types import SpeakingOfficialPromotionResult


class OfficialSpeakingPromotionApiError(Exception):
    def __init__(self, status_code: int, detail: dict | str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(str(detail))


def _result_to_out(result: SpeakingOfficialPromotionResult) -> SpeakingOfficialPromotionOut:
    safe = result.to_student_safe_dict()
    return SpeakingOfficialPromotionOut(
        promotion_success=bool(safe["promotion_success"]),
        old_cefr=str(safe["old_cefr"]),
        new_cefr=str(safe["new_cefr"]),
        new_learning_stage=int(safe.get("new_learning_stage") or 0),
        summary=str(safe.get("summary") or ""),
        reason=safe.get("reason"),
        assessment_id=str(safe.get("assessment_id") or ""),
        attempt_id=str(safe.get("attempt_id") or ""),
        promoted_at=str(safe.get("promoted_at") or ""),
        already_promoted=bool(safe.get("already_promoted")),
        ready_for_new_journey=bool(safe.get("ready_for_new_journey")),
    )


def _denial_status_code(result: SpeakingOfficialPromotionResult) -> int:
    reason = (result.reason or "").lower()
    if "no speaking promotion assessment" in reason or "no progression row" in reason:
        return 404
    return 409


async def apply_speaking_official_promotion_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    assessment_id: str | None = None,
    attempt_id: str | None = None,
) -> SpeakingOfficialPromotionOut:
    if await ensure_progression_row(db, student_id=student_id, language_id=language_id) is None:
        raise OfficialSpeakingPromotionApiError(
            503,
            {
                "promotion_success": False,
                "reason": PROGRESSION_UNAVAILABLE_REASON,
                "progression_available": False,
            },
        )

    row = await lock_speaking_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        raise OfficialSpeakingPromotionApiError(
            404,
            {"promotion_success": False, "reason": "No progression row found."},
        )

    payload = dict(row.promotion_readiness_json or {})
    already = False
    if attempt_id and is_attempt_already_promoted(payload, attempt_id):
        already = True
    if assessment_id and is_assessment_already_promoted(payload, assessment_id):
        already = True

    result = await apply_speaking_official_promotion(
        db,
        student_id=student_id,
        language_id=language_id,
        assessment_id=assessment_id,
        attempt_id=attempt_id,
        locked_row=row,
    )

    if not result.success:
        raise OfficialSpeakingPromotionApiError(
            _denial_status_code(result),
            {
                "promotion_success": False,
                "reason": result.reason,
                "old_cefr": result.old_cefr,
                "new_cefr": result.new_cefr,
                "assessment_id": result.assessment_id,
                "attempt_id": result.attempt_id,
            },
        )

    response = _result_to_out(result)
    if already or result.already_promoted:
        raise OfficialSpeakingPromotionApiError(409, response.model_dump())
    return response
