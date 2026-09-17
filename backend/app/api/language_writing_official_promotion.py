"""Writing Official Promotion API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.language_writing_official_promotion import WritingOfficialPromotionOut
from app.services.language_access_service import require_language_learning_ready
from app.services.language_subscription_service import get_default_language
from app.services.language_writing_official_promotion_api import (
    OfficialWritingPromotionApiError,
    apply_writing_official_promotion_api,
)

router = APIRouter(
    prefix="/student/languages/writing",
    tags=["Language Writing Official Promotion"],
)


def _raise_api_error(exc: OfficialWritingPromotionApiError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/promote", response_model=WritingOfficialPromotionOut)
async def writing_official_promote(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> WritingOfficialPromotionOut:
    language = await get_default_language(db)
    try:
        result = await apply_writing_official_promotion_api(
            db,
            student_id=student.id,
            language_id=language.id,
        )
    except OfficialWritingPromotionApiError as exc:
        _raise_api_error(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result
