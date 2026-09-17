"""Speaking Official Promotion API routes (S20)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.language_speaking_official_promotion import (
    SpeakingOfficialPromotionIn,
    SpeakingOfficialPromotionOut,
)
from app.services.language_access_service import require_language_learning_ready
from app.services.language_subscription_service import get_default_language
from app.services.language_speaking_official_promotion_api import (
    OfficialSpeakingPromotionApiError,
    apply_speaking_official_promotion_api,
)

router = APIRouter(
    prefix="/student/languages/speaking",
    tags=["Language Speaking Official Promotion"],
)


def _raise_api_error(exc: OfficialSpeakingPromotionApiError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/promote", response_model=SpeakingOfficialPromotionOut)
async def speaking_official_promote(
    body: SpeakingOfficialPromotionIn | None = None,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> SpeakingOfficialPromotionOut:
    language = await get_default_language(db)
    payload = body or SpeakingOfficialPromotionIn()
    try:
        result = await apply_speaking_official_promotion_api(
            db,
            student_id=student.id,
            language_id=language.id,
            assessment_id=payload.assessment_id,
            attempt_id=payload.attempt_id,
        )
    except OfficialSpeakingPromotionApiError as exc:
        _raise_api_error(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result
