"""Guided Discussion API routes (E3) — Live Voice Discussion."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.language_speaking_discussion import (
    DiscussionOpenIn,
    DiscussionRuntimeOut,
    DiscussionSubmitIn,
)
from app.services.language_access_service import require_language_learning_ready
from app.services.language_subscription_service import get_default_language
from app.services.language_speaking_discussion_api import (
    DiscussionApiError,
    advance_discussion_api,
    get_discussion_api,
    open_discussion_api,
    submit_discussion_api,
)
from app.services.language_speaking_discussion_api.service import submit_discussion_voice_api

router = APIRouter(
    prefix="/student/languages/speaking/discussion",
    tags=["Language Speaking Guided Discussion"],
)


def _raise(exc: DiscussionApiError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/open", response_model=DiscussionRuntimeOut)
async def open_guided_discussion(
    body: DiscussionOpenIn | None = None,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> DiscussionRuntimeOut:
    language = await get_default_language(db)
    payload = body or DiscussionOpenIn()
    try:
        result = await open_discussion_api(
            db,
            student_id=student.id,
            language_id=language.id,
            package_id=payload.package_id,
            force_restart=payload.force_restart,
        )
    except DiscussionApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result


@router.get("/active", response_model=DiscussionRuntimeOut)
async def get_active_discussion(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> DiscussionRuntimeOut:
    language = await get_default_language(db)
    try:
        return await get_discussion_api(
            db, student_id=student.id, language_id=language.id
        )
    except DiscussionApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")


@router.post("/submit", response_model=DiscussionRuntimeOut)
async def submit_guided_discussion(
    body: DiscussionSubmitIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> DiscussionRuntimeOut:
    language = await get_default_language(db)
    try:
        result = await submit_discussion_api(
            db,
            student_id=student.id,
            language_id=language.id,
            student_response=body.student_response,
        )
    except DiscussionApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result


@router.post("/submit-voice", response_model=DiscussionRuntimeOut)
async def submit_guided_discussion_voice(
    file: UploadFile = File(...),
    mime_type: str | None = Form(default=None),
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> DiscussionRuntimeOut:
    language = await get_default_language(db)
    audio = await file.read()
    resolved_mime = (
        (mime_type or file.content_type or "audio/webm").split(";")[0].strip().lower()
    )
    try:
        result = await submit_discussion_voice_api(
            db,
            student_id=student.id,
            language_id=language.id,
            audio_bytes=audio,
            mime_type=resolved_mime,
        )
    except DiscussionApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result


@router.post("/advance", response_model=DiscussionRuntimeOut)
async def advance_guided_discussion(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> DiscussionRuntimeOut:
    language = await get_default_language(db)
    try:
        result = await advance_discussion_api(
            db, student_id=student.id, language_id=language.id
        )
    except DiscussionApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result
