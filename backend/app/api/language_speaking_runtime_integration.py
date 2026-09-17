"""Speaking runtime integration routes — Start Learning orchestration."""



from __future__ import annotations



from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession



from app.db.session import get_db
from app.models.user import User
from app.schemas.language_speaking_runtime_integration import (
    EnsureLearningPackageIn,
    EnsureLearningPackageOut,
    StartLearningIn,
    StartLearningOut,
)
from app.services.language_access_service import require_language_learning_ready
from app.services.language_subscription_service import get_default_language
from app.services.language_speaking_runtime_api import (
    RuntimeIntegrationError,
    ensure_learning_package_for_journey,
    start_learning_runtime,
)



router = APIRouter(
    prefix="/student/languages/speaking/runtime",
    tags=["Language Speaking Runtime Integration"],
)





def _raise(exc: RuntimeIntegrationError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc





@router.post("/ensure-package", response_model=EnsureLearningPackageOut)
async def ensure_package(
    body: EnsureLearningPackageIn | None = None,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> EnsureLearningPackageOut:
    language = await get_default_language(db)
    payload = body or EnsureLearningPackageIn()
    try:
        result = await ensure_learning_package_for_journey(
            db,
            student_id=student.id,
            language_id=language.id,
            author_mode=payload.author_mode,
            use_cache=payload.use_cache,
        )
    except RuntimeIntegrationError as exc:
        _raise(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return EnsureLearningPackageOut(
        success=True,
        reused=result.reused,
        cached=result.cached,
        package_id=result.package_id,
        content_item_id=result.content_item_id,
        status=result.status,
        constraints_fingerprint=result.constraints_fingerprint,
        content_fingerprint=result.content_fingerprint,
        package=result.package,
    )





@router.post("/start-learning", response_model=StartLearningOut)
async def start_learning(
    body: StartLearningIn | None = None,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> StartLearningOut:
    language = await get_default_language(db)
    payload = body or StartLearningIn()
    try:
        result = await start_learning_runtime(
            db,
            student_id=student.id,
            language_id=language.id,
            author_mode=payload.author_mode,
            use_cache=payload.use_cache,
            force_restart_lesson=payload.force_restart_lesson,
        )
    except RuntimeIntegrationError as exc:
        _raise(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return StartLearningOut(**result)
