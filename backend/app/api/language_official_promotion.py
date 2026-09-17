"""Listening Official Promotion API routes (PR-3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.language_official_promotion import ListeningOfficialPromotionOut
from app.services.language_access_service import require_language_learning_ready
from app.services.language_official_promotion_api import (
    OfficialPromotionApiError,
    apply_listening_official_promotion_api,
)
from app.services.language_subscription_service import get_default_language

router = APIRouter(
    prefix="/student/languages/listening",
    tags=["Language Listening Official Promotion"],
)


def _raise_api_error(exc: OfficialPromotionApiError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/promote", response_model=ListeningOfficialPromotionOut)
async def listening_official_promote(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> ListeningOfficialPromotionOut:
    language = await get_default_language(db)
    try:
        result = await apply_listening_official_promotion_api(
            db,
            student_id=student.id,
            language_id=language.id,
        )
    except OfficialPromotionApiError as exc:
        _raise_api_error(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result
