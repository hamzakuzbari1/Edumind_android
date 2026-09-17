"""API twin for Live Speaking Bridge."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.language_speaking_live_bridge import LiveBridgeOut
from app.services.language_speaking_live_bridge.engine import (
    LiveBridgeError,
    LiveBridgeView,
    build_preparation,
    complete_rehearsal,
    get_live_bridge_view,
    respond_rehearsal_turn,
    start_voice_rehearsal,
    submit_rehearsal_turn,
)


class LiveBridgeApiError(Exception):
    def __init__(self, status_code: int, detail: str, code: str = "") -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(detail)


def _map(exc: LiveBridgeError) -> LiveBridgeApiError:
    status = {
        "not_found": 404,
        "no_package": 404,
        "no_progression": 404,
        "no_case": 422,
        "not_frozen": 409,
        "no_rehearsal": 409,
        "no_scenario": 409,
        "corrupt": 422,
        "empty_response": 400,
        "empty_audio": 400,
        "stt_unavailable": 503,
    }.get(exc.code, 400)
    return LiveBridgeApiError(status, exc.message, exc.code)


def _out(view: LiveBridgeView) -> LiveBridgeOut:
    return LiveBridgeOut(**view.to_dict())


async def get_live_bridge_api(
    db: AsyncSession, *, student_id: int, language_id: int
) -> LiveBridgeOut:
    try:
        return _out(await get_live_bridge_view(db, student_id=student_id, language_id=language_id))
    except LiveBridgeError as exc:
        raise _map(exc) from exc


async def prepare_speaking_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package_id: str | None = None,
) -> LiveBridgeOut:
    try:
        return _out(
            await build_preparation(
                db,
                student_id=student_id,
                language_id=language_id,
                package_id=package_id,
            )
        )
    except LiveBridgeError as exc:
        raise _map(exc) from exc


async def start_rehearsal_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package_id: str | None = None,
) -> LiveBridgeOut:
    try:
        return _out(
            await start_voice_rehearsal(
                db,
                student_id=student_id,
                language_id=language_id,
                package_id=package_id,
            )
        )
    except LiveBridgeError as exc:
        raise _map(exc) from exc


async def submit_rehearsal_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    student_text: str,
) -> LiveBridgeOut:
    try:
        return _out(
            await submit_rehearsal_turn(
                db,
                student_id=student_id,
                language_id=language_id,
                student_text=student_text,
            )
        )
    except LiveBridgeError as exc:
        raise _map(exc) from exc
    except ValueError as exc:
        raise LiveBridgeApiError(400, str(exc), "empty_response") from exc


async def respond_rehearsal_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    audio_bytes: bytes,
    mime_type: str,
) -> tuple[LiveBridgeOut, dict]:
    """M12.3 voice turn: STT → Claude Scene Director → persist → TTS → response."""
    try:
        view, turn = await respond_rehearsal_turn(
            db,
            student_id=student_id,
            language_id=language_id,
            audio_bytes=audio_bytes,
            mime_type=mime_type,
        )
        return _out(view), turn
    except LiveBridgeError as exc:
        raise _map(exc) from exc
    except ValueError as exc:
        raise LiveBridgeApiError(400, str(exc), "empty_response") from exc


async def complete_rehearsal_api(
    db: AsyncSession, *, student_id: int, language_id: int
) -> LiveBridgeOut:
    try:
        return _out(await complete_rehearsal(db, student_id=student_id, language_id=language_id))
    except LiveBridgeError as exc:
        raise _map(exc) from exc
