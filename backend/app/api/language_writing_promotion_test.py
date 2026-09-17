"""Writing Promotion Assessment (WPA) API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.language_writing_promotion_test import (
    WritingPromotionStartOut,
    WritingPromotionStatusOut,
    WritingPromotionSubmitIn,
    WritingPromotionSubmitOut,
)
from app.services.language_access_service import require_language_learning_ready
from app.services.language_subscription_service import get_default_language
from app.services.language_writing_promotion_test_api import (
    WritingPromotionTestApiError,
    get_writing_promotion_test_status,
    start_writing_promotion_test,
    submit_writing_promotion_test_api,
)

router = APIRouter(
    prefix="/student/languages/writing/promotion-test",
    tags=["Language Writing Promotion Test"],
)


def _raise_api_error(exc: WritingPromotionTestApiError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/status", response_model=WritingPromotionStatusOut)
async def writing_promotion_test_status(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> WritingPromotionStatusOut:
    language = await get_default_language(db)
    return await get_writing_promotion_test_status(
        db,
        student_id=student.id,
        language_id=language.id,
    )


@router.post("/start", response_model=WritingPromotionStartOut)
async def writing_promotion_test_start(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> WritingPromotionStartOut:
    language = await get_default_language(db)
    try:
        result = await start_writing_promotion_test(
            db,
            student_id=student.id,
            language_id=language.id,
        )
    except WritingPromotionTestApiError as exc:
        _raise_api_error(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result


@router.post("/submit", response_model=WritingPromotionSubmitOut)
async def writing_promotion_test_submit(
    body: WritingPromotionSubmitIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> WritingPromotionSubmitOut:
    language = await get_default_language(db)
    try:
        result = await submit_writing_promotion_test_api(
            db,
            student_id=student.id,
            language_id=language.id,
            session_id=body.session_id,
            submissions=body.submissions,
        )
    except WritingPromotionTestApiError as exc:
        _raise_api_error(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result
