"""Thin API twin for Guided Discussion (E3) + E4 evaluation handoff + voice I/O."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.language_speaking_discussion import DiscussionRuntimeOut
from app.services.language_speaking_discussion.engine import (
    DiscussionRuntimeError,
    DiscussionView,
    advance_discussion_step,
    get_discussion_view,
    open_discussion,
    submit_discussion_response,
)
from app.services.language_speaking_discussion.voice_io import (
    DiscussionVoiceError,
    transcribe_discussion_audio,
    tts_discussion_line,
)
from app.services.language_speaking_discussion_eval.adapter import (
    maybe_map_discussion_turn_to_evaluation,
)
from app.services.language_speaking_discussion_eval.types import DiscussionProductionMode
from app.services.language_speaking_educational_package.persistence import (
    get_package_item_by_id,
    package_from_item,
)

logger = logging.getLogger(__name__)


class DiscussionApiError(Exception):
    def __init__(self, status_code: int, detail: str, code: str = "") -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(detail)


def _map(exc: DiscussionRuntimeError) -> DiscussionApiError:
    status = {
        "not_found": 404,
        "no_package": 404,
        "no_runtime": 404,
        "no_progression": 404,
        "lesson_required": 409,
        "lesson_not_ready": 409,
        "not_frozen": 409,
        "fingerprint_mismatch": 409,
        "stale_runtime": 409,
        "already_complete": 409,
        "step_turn_limit": 409,
        "answer_required": 409,
        "empty_response": 400,
        "no_steps": 422,
        "corrupt": 422,
    }.get(exc.code, 400)
    return DiscussionApiError(status, exc.message, exc.code)


def _map_voice(exc: DiscussionVoiceError) -> DiscussionApiError:
    status = {
        "empty_audio": 400,
        "stt_unavailable": 503,
    }.get(exc.code, 400)
    return DiscussionApiError(status, exc.message, exc.code)


async def _with_tts(
    view: DiscussionView,
    *,
    student_transcript: str | None = None,
    heard: bool | None = None,
) -> DiscussionRuntimeOut:
    data = view.to_dict()
    utterance = ""
    la = data.get("latest_assistant") or {}
    if isinstance(la, dict):
        utterance = str(la.get("utterance") or "").strip()
    tts = await tts_discussion_line(utterance) if utterance else {
        "audio_b64": None,
        "audio_mime": None,
    }
    return DiscussionRuntimeOut(
        **data,
        audio_b64=tts.get("audio_b64"),
        audio_mime=tts.get("audio_mime"),
        student_transcript=student_transcript,
        heard=heard,
    )


def idle_discussion_api() -> DiscussionRuntimeOut:
    return DiscussionRuntimeOut(
        runtime_version="3.0.0",
        state={
            "schema_version": "3.0.0",
            "package_id": None,
            "content_item_id": None,
            "content_fingerprint": "",
            "phase": "idle",
            "step_index": 0,
            "current_step_id": "",
            "assistant_turns_used": 0,
            "answered_step_ids": [],
            "corrections_shown": [],
            "turns": [],
            "completed": False,
            "ready_for_alex": False,
            "opening_shown": False,
            "started_at": "",
            "updated_at": "",
            "status": "idle",
        },
        package_title="",
        current_step=None,
        steps_total=0,
        opening_move="",
        closing_move="",
        latest_assistant=None,
        provider="",
        package_snippet={},
    )


def _resolve_step(package, state):
    steps = package.discussion.steps
    if not steps:
        return None
    if state.current_step_id:
        for step in steps:
            if step.step_id == state.current_step_id:
                return step
    idx = min(max(0, state.step_index), len(steps) - 1)
    return steps[idx]


async def _handoff_after_submit(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    view: DiscussionView,
    student_response: str,
    production_mode: DiscussionProductionMode = DiscussionProductionMode.text,
) -> None:
    """E4: map eligible turns into S7. Never alters the student DiscussionView."""
    package_id = view.state.package_id
    if not package_id:
        return
    item = await get_package_item_by_id(
        db, student_id=student_id, language_id=language_id, package_id=package_id
    )
    if item is None:
        return
    package = package_from_item(item)
    if package is None:
        return
    step = _resolve_step(package, view.state)
    try:
        await maybe_map_discussion_turn_to_evaluation(
            db,
            student_id=student_id,
            language_id=language_id,
            package=package,
            state=view.state,
            step=step,
            student_response=student_response,
            production_mode=production_mode,
        )
    except Exception:  # noqa: BLE001 — pedagogy must remain identical if S7 is down
        logger.exception(
            "E4 discussion evaluation handoff failed package=%s step=%s",
            package_id,
            getattr(step, "step_id", None),
        )


async def _maybe_auto_advance(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    view: DiscussionView,
) -> DiscussionView:
    """When Claude signals readiness, advance the frozen ladder so voice stays continuous."""
    la = view.latest_assistant or {}
    if view.state.completed or not la.get("can_advance"):
        return view
    try:
        return await advance_discussion_step(
            db, student_id=student_id, language_id=language_id
        )
    except DiscussionRuntimeError:
        return view


async def open_discussion_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package_id: str | None = None,
    force_restart: bool = False,
) -> DiscussionRuntimeOut:
    try:
        view = await open_discussion(
            db,
            student_id=student_id,
            language_id=language_id,
            package_id=package_id,
            force_restart=force_restart,
        )
    except DiscussionRuntimeError as exc:
        raise _map(exc) from exc
    return await _with_tts(view)


async def get_discussion_api(
    db: AsyncSession, *, student_id: int, language_id: int
) -> DiscussionRuntimeOut:
    try:
        view = await get_discussion_view(
            db, student_id=student_id, language_id=language_id
        )
    except DiscussionRuntimeError as exc:
        if exc.code in {"no_runtime", "no_package", "not_found", "stale_runtime"}:
            return idle_discussion_api()
        raise _map(exc) from exc
    # Keep /active fast — TTS is attached on open/submit/advance (and FE re-open).
    return DiscussionRuntimeOut(**view.to_dict())


async def submit_discussion_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    student_response: str,
) -> DiscussionRuntimeOut:
    try:
        view = await submit_discussion_response(
            db,
            student_id=student_id,
            language_id=language_id,
            student_response=student_response,
        )
    except DiscussionRuntimeError as exc:
        raise _map(exc) from exc
    await _handoff_after_submit(
        db,
        student_id=student_id,
        language_id=language_id,
        view=view,
        student_response=student_response,
        production_mode=DiscussionProductionMode.text,
    )
    view = await _maybe_auto_advance(
        db, student_id=student_id, language_id=language_id, view=view
    )
    return await _with_tts(view, student_transcript=student_response, heard=True)


async def submit_discussion_voice_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    audio_bytes: bytes,
    mime_type: str,
) -> DiscussionRuntimeOut:
    """Voice turn: GPT STT → Claude tutor (+ optional auto-advance) → GPT TTS."""
    try:
        transcript, _confidence = await transcribe_discussion_audio(
            audio_bytes,
            mime_type,
            student_id=student_id,
            language_id=language_id,
        )
    except DiscussionVoiceError as exc:
        raise _map_voice(exc) from exc

    if not transcript:
        # Gentle retry — no tutor call, no state mutation.
        reprompt = "Sorry — I didn't catch that. Say it one more time?"
        tts = await tts_discussion_line(reprompt)
        try:
            view = await get_discussion_view(
                db, student_id=student_id, language_id=language_id
            )
        except DiscussionRuntimeError as exc:
            raise _map(exc) from exc
        data = view.to_dict()
        data["latest_assistant"] = {
            "utterance": reprompt,
            "correction": None,
            "can_advance": False,
        }
        return DiscussionRuntimeOut(
            **data,
            audio_b64=tts.get("audio_b64"),
            audio_mime=tts.get("audio_mime"),
            student_transcript="",
            heard=False,
        )

    try:
        view = await submit_discussion_response(
            db,
            student_id=student_id,
            language_id=language_id,
            student_response=transcript,
        )
    except DiscussionRuntimeError as exc:
        raise _map(exc) from exc

    await _handoff_after_submit(
        db,
        student_id=student_id,
        language_id=language_id,
        view=view,
        student_response=transcript,
        production_mode=DiscussionProductionMode.spoken,
    )
    view = await _maybe_auto_advance(
        db, student_id=student_id, language_id=language_id, view=view
    )
    return await _with_tts(view, student_transcript=transcript, heard=True)


async def advance_discussion_api(
    db: AsyncSession, *, student_id: int, language_id: int
) -> DiscussionRuntimeOut:
    try:
        view = await advance_discussion_step(
            db, student_id=student_id, language_id=language_id
        )
    except DiscussionRuntimeError as exc:
        raise _map(exc) from exc
    return await _with_tts(view)
