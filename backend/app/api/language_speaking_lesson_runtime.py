"""Speaking Lesson Runtime API routes (E2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.language_speaking_lesson_runtime import (
    LessonRuntimeMarkBlockIn,
    LessonRuntimeMarkVocabIn,
    LessonRuntimeOpenIn,
    LessonRuntimeOut,
)
from app.services.language_access_service import require_language_learning_ready
from app.services.language_subscription_service import get_default_language
from app.services.language_speaking_lesson_runtime_api import (
    LessonRuntimeApiError,
    advance_lesson_runtime_api,
    get_lesson_runtime_api,
    mark_block_api,
    mark_mini_prep_api,
    mark_vocab_api,
    open_lesson_runtime_api,
)

router = APIRouter(
    prefix="/student/languages/speaking/lesson-runtime",
    tags=["Language Speaking Lesson Runtime"],
)


def _raise(exc: LessonRuntimeApiError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/open", response_model=LessonRuntimeOut)
async def open_runtime(
    body: LessonRuntimeOpenIn | None = None,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> LessonRuntimeOut:
    language = await get_default_language(db)
    payload = body or LessonRuntimeOpenIn()
    try:
        result = await open_lesson_runtime_api(
            db,
            student_id=student.id,
            language_id=language.id,
            package_id=payload.package_id,
            force_restart=payload.force_restart,
        )
    except LessonRuntimeApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result


@router.get("/active", response_model=LessonRuntimeOut)
async def get_active_runtime(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> LessonRuntimeOut:
    language = await get_default_language(db)
    try:
        result = await get_lesson_runtime_api(
            db, student_id=student.id, language_id=language.id
        )
        await db.commit()
        return result
    except LessonRuntimeApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")


@router.post("/advance", response_model=LessonRuntimeOut)
async def advance_runtime(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> LessonRuntimeOut:
    language = await get_default_language(db)
    try:
        result = await advance_lesson_runtime_api(
            db, student_id=student.id, language_id=language.id
        )
    except LessonRuntimeApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result


@router.post("/vocabulary/viewed", response_model=LessonRuntimeOut)
async def mark_vocab(
    body: LessonRuntimeMarkVocabIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> LessonRuntimeOut:
    language = await get_default_language(db)
    try:
        result = await mark_vocab_api(
            db,
            student_id=student.id,
            language_id=language.id,
            vocabulary_id=body.vocabulary_id,
        )
    except LessonRuntimeApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result


@router.post("/teaching-blocks/viewed", response_model=LessonRuntimeOut)
async def mark_block(
    body: LessonRuntimeMarkBlockIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> LessonRuntimeOut:
    language = await get_default_language(db)
    try:
        result = await mark_block_api(
            db,
            student_id=student.id,
            language_id=language.id,
            block_id=body.block_id,
        )
    except LessonRuntimeApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result


@router.post("/mini-practice/prep-complete", response_model=LessonRuntimeOut)
async def mark_mini_prep(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> LessonRuntimeOut:
    language = await get_default_language(db)
    try:
        result = await mark_mini_prep_api(
            db, student_id=student.id, language_id=language.id
        )
    except LessonRuntimeApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result
