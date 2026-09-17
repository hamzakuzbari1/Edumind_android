"""M10 Live Speaking Bridge API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.language_speaking_live_bridge import (
    LiveBridgeOut,
    LiveBridgePrepareIn,
    LiveBridgeRehearsalStartIn,
    LiveBridgeRehearsalTurnIn,
    LiveBridgeRespondOut,
)
from app.services.language_access_service import require_language_learning_ready
from app.services.language_subscription_service import get_default_language
from app.services.language_speaking_live_bridge_api import (
    LiveBridgeApiError,
    complete_rehearsal_api,
    get_live_bridge_api,
    prepare_speaking_api,
    respond_rehearsal_api,
    start_rehearsal_api,
    submit_rehearsal_api,
)

_MAX_RESPOND_AUDIO_BYTES = 8 * 1024 * 1024  # one Scene Practice turn recording

router = APIRouter(
    prefix="/student/languages/speaking/live-bridge",
    tags=["Language Speaking Live Bridge"],
)


def _raise(exc: LiveBridgeApiError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/active", response_model=LiveBridgeOut)
async def get_active_live_bridge(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> LiveBridgeOut:
    language = await get_default_language(db)
    try:
        return await get_live_bridge_api(
            db, student_id=student.id, language_id=language.id
        )
    except LiveBridgeApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")


@router.post("/prepare", response_model=LiveBridgeOut)
async def prepare_speaking_bridge(
    body: LiveBridgePrepareIn | None = None,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> LiveBridgeOut:
    language = await get_default_language(db)
    payload = body or LiveBridgePrepareIn()
    try:
        result = await prepare_speaking_api(
            db,
            student_id=student.id,
            language_id=language.id,
            package_id=payload.package_id,
        )
    except LiveBridgeApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result


@router.post("/rehearsal/start", response_model=LiveBridgeOut)
async def start_rehearsal_bridge(
    body: LiveBridgeRehearsalStartIn | None = None,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> LiveBridgeOut:
    language = await get_default_language(db)
    payload = body or LiveBridgeRehearsalStartIn()
    try:
        result = await start_rehearsal_api(
            db,
            student_id=student.id,
            language_id=language.id,
            package_id=payload.package_id,
        )
    except LiveBridgeApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result


@router.post("/rehearsal/turn", response_model=LiveBridgeOut)
async def submit_rehearsal_bridge_turn(
    body: LiveBridgeRehearsalTurnIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> LiveBridgeOut:
    language = await get_default_language(db)
    try:
        result = await submit_rehearsal_api(
            db,
            student_id=student.id,
            language_id=language.id,
            student_text=body.student_text,
        )
    except LiveBridgeApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result


@router.post("/rehearsal/respond", response_model=LiveBridgeRespondOut)
async def respond_rehearsal_bridge_turn(
    audio: UploadFile = File(...),
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> LiveBridgeRespondOut:
    """M12 voice Scene Practice turn: audio in → STT → Claude → persist → TTS → out."""
    language = await get_default_language(db)
    audio_bytes = await audio.read(_MAX_RESPOND_AUDIO_BYTES + 1)
    if len(audio_bytes) > _MAX_RESPOND_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Recording is too large for one turn.")
    try:
        bridge, turn = await respond_rehearsal_api(
            db,
            student_id=student.id,
            language_id=language.id,
            audio_bytes=audio_bytes,
            mime_type=audio.content_type or "audio/webm",
        )
    except LiveBridgeApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return LiveBridgeRespondOut(bridge=bridge, **turn)


@router.post("/rehearsal/complete", response_model=LiveBridgeOut)
async def complete_rehearsal_bridge(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> LiveBridgeOut:
    language = await get_default_language(db)
    try:
        result = await complete_rehearsal_api(
            db, student_id=student.id, language_id=language.id
        )
    except LiveBridgeApiError as exc:
        _raise(exc)
        raise AssertionError("unreachable")
    await db.commit()
    return result
