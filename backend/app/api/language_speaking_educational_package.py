"""Speaking Learning Package API routes (E1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.language_speaking_educational_package import (
    SpeakingLearningPackageCreateIn,
    SpeakingLearningPackageOut,
    SpeakingLearningPackageStatusOut,
)
from app.services.language_access_service import require_language_learning_ready
from app.services.language_subscription_service import get_default_language
from app.services.language_speaking_educational_package_api import (
    SpeakingLearningPackageApiError,
    create_speaking_learning_package_api,
    get_speaking_learning_package_api,
    get_speaking_learning_package_status_api,
)

router = APIRouter(
    prefix="/student/languages/speaking/learning-packages",
    tags=["Language Speaking Learning Package"],
)


def _raise_api_error(exc: SpeakingLearningPackageApiError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("", response_model=SpeakingLearningPackageOut)
async def create_learning_package(
    body: SpeakingLearningPackageCreateIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> SpeakingLearningPackageOut:
    language = await get_default_language(db)
    try:
        result = await create_speaking_learning_package_api(
            db,
            student_id=student.id,
            language_id=language.id,
            constraints=body.constraints,
            author_mode=body.author_mode,
            use_cache=body.use_cache,
        )
    except SpeakingLearningPackageApiError as exc:
        _raise_api_error(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result


@router.get("/{package_id}", response_model=SpeakingLearningPackageOut)
async def get_learning_package(
    package_id: str,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> SpeakingLearningPackageOut:
    language = await get_default_language(db)
    try:
        return await get_speaking_learning_package_api(
            db,
            student_id=student.id,
            language_id=language.id,
            package_id=package_id,
        )
    except SpeakingLearningPackageApiError as exc:
        _raise_api_error(exc)
        raise AssertionError("unreachable")


@router.get("/{package_id}/status", response_model=SpeakingLearningPackageStatusOut)
async def get_learning_package_status(
    package_id: str,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> SpeakingLearningPackageStatusOut:
    language = await get_default_language(db)
    try:
        return await get_speaking_learning_package_status_api(
            db,
            student_id=student.id,
            language_id=language.id,
            package_id=package_id,
        )
    except SpeakingLearningPackageApiError as exc:
        _raise_api_error(exc)
        raise AssertionError("unreachable")
