"""API orchestration for Writing Official Promotion."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.language_writing_official_promotion import WritingOfficialPromotionOut
from app.services.language_progression_service import PROGRESSION_UNAVAILABLE_REASON, ensure_progression_row
from app.services.language_writing_official_promotion import apply_writing_official_promotion
from app.services.language_writing_official_promotion.types import WritingOfficialPromotionResult
from app.services.language_writing_progression.locking import lock_writing_progression_row
from app.services.language_writing_promotion_test.storage import latest_attempt


class OfficialWritingPromotionApiError(Exception):
    def __init__(self, status_code: int, detail: dict | str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(str(detail))


def _result_to_out(result: WritingOfficialPromotionResult) -> WritingOfficialPromotionOut:
    return WritingOfficialPromotionOut(
        promotion_success=result.success,
        old_cefr=result.old_cefr,
        new_cefr=result.new_cefr,
        new_learning_stage=1 if result.success else 0,
        summary=result.reason,
        session_id=result.session_id,
        reason=None if result.success else result.reason,
    )


def _denial_status_code(result: WritingOfficialPromotionResult) -> int:
    reason = (result.reason or "").lower()
    if "no wpa attempt" in reason or "no progression row" in reason:
        return 404
    return 409


async def apply_writing_official_promotion_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> WritingOfficialPromotionOut:
    if await ensure_progression_row(db, student_id=student_id, language_id=language_id) is None:
        raise OfficialWritingPromotionApiError(
            503,
            {
                "promotion_success": False,
                "reason": PROGRESSION_UNAVAILABLE_REASON,
                "progression_available": False,
            },
        )

    row = await lock_writing_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        raise OfficialWritingPromotionApiError(
            404,
            {"promotion_success": False, "reason": "No progression row found."},
        )

    payload = dict(row.promotion_readiness_json or {})
    attempt = latest_attempt(payload)
    already_promoted = False
    if attempt:
        sid = str(attempt.get("session_id", ""))
        prom_bucket = payload.get("writing_official_promotions") or {}
        promoted_ids = set(prom_bucket.get("promoted_session_ids") or [])
        already_promoted = sid in promoted_ids

    result = await apply_writing_official_promotion(
        db,
        student_id=student_id,
        language_id=language_id,
        locked_row=row,
    )

    if not result.success:
        raise OfficialWritingPromotionApiError(
            _denial_status_code(result),
            {
                "promotion_success": False,
                "reason": result.reason,
                "old_cefr": result.old_cefr,
                "new_cefr": result.new_cefr,
            },
        )

    response = _result_to_out(result)
    if already_promoted:
        raise OfficialWritingPromotionApiError(409, response.model_dump())
    return response
