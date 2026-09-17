"""Listening Promotion Test API routes (PR-2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.language_promotion_test import (
    PromotionTestStartOut,
    PromotionTestStatusOut,
    PromotionTestSubmitIn,
    PromotionTestSubmitOut,
)
from app.services.language_access_service import require_language_learning_ready
from app.services.language_promotion_test_api import (
    PromotionTestApiError,
    get_listening_promotion_test_status,
    start_listening_promotion_test,
    submit_listening_promotion_test_api,
)
from app.services.language_subscription_service import get_default_language

router = APIRouter(
    prefix="/student/languages/listening/promotion-test",
    tags=["Language Listening Promotion Test"],
)


def _raise_api_error(exc: PromotionTestApiError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/status", response_model=PromotionTestStatusOut)
async def promotion_test_status(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> PromotionTestStatusOut:
    language = await get_default_language(db)
    return await get_listening_promotion_test_status(
        db,
        student_id=student.id,
        language_id=language.id,
    )


@router.post("/start", response_model=PromotionTestStartOut)
async def promotion_test_start(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> PromotionTestStartOut:
    language = await get_default_language(db)
    try:
        result = await start_listening_promotion_test(
            db,
            student_id=student.id,
            language_id=language.id,
        )
    except PromotionTestApiError as exc:
        _raise_api_error(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result


@router.post("/submit", response_model=PromotionTestSubmitOut)
async def promotion_test_submit(
    body: PromotionTestSubmitIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> PromotionTestSubmitOut:
    language = await get_default_language(db)
    try:
        result = await submit_listening_promotion_test_api(
            db,
            student_id=student.id,
            language_id=language.id,
            session_id=body.session_id,
            answers=body.answers,
        )
    except PromotionTestApiError as exc:
        _raise_api_error(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result
