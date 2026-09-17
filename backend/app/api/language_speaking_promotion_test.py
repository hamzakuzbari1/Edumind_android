"""Speaking Promotion Assessment (SPA) API routes — S18 blueprint surfaces."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.language_speaking_promotion_test import (
    SpeakingPromotionAssessmentCreateOut,
    SpeakingPromotionAssessmentGetOut,
    SpeakingPromotionAssessmentStatusOut,
)
from app.services.language_access_service import require_language_learning_ready
from app.services.language_subscription_service import get_default_language
from app.services.language_speaking_promotion_test_api import (
    SpeakingPromotionAssessmentApiError,
    create_speaking_promotion_assessment_api,
    get_speaking_promotion_assessment_api,
    get_speaking_promotion_assessment_status,
)

router = APIRouter(
    prefix="/student/languages/speaking/promotion-assessment",
    tags=["Language Speaking Promotion Assessment"],
)


def _raise_api_error(exc: SpeakingPromotionAssessmentApiError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/status", response_model=SpeakingPromotionAssessmentStatusOut)
async def speaking_promotion_assessment_status(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> SpeakingPromotionAssessmentStatusOut:
    language = await get_default_language(db)
    return await get_speaking_promotion_assessment_status(
        db,
        student_id=student.id,
        language_id=language.id,
    )


@router.post("", response_model=SpeakingPromotionAssessmentCreateOut)
async def speaking_promotion_assessment_create(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> SpeakingPromotionAssessmentCreateOut:
    language = await get_default_language(db)
    try:
        result = await create_speaking_promotion_assessment_api(
            db,
            student_id=student.id,
            language_id=language.id,
        )
    except SpeakingPromotionAssessmentApiError as exc:
        _raise_api_error(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result


@router.get("/{assessment_id}", response_model=SpeakingPromotionAssessmentGetOut)
async def speaking_promotion_assessment_get(
    assessment_id: str,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> SpeakingPromotionAssessmentGetOut:
    language = await get_default_language(db)
    try:
        return await get_speaking_promotion_assessment_api(
            db,
            student_id=student.id,
            language_id=language.id,
            assessment_id=assessment_id,
        )
    except SpeakingPromotionAssessmentApiError as exc:
        _raise_api_error(exc)
        raise AssertionError("unreachable")
