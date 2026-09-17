"""Student Grammar Module API.



POST /api/student/grammar/lesson/start — generate-only lesson package.

POST /api/student/grammar/activity/complete — Wave B evidence→mastery→progression.

"""



from __future__ import annotations



import logging
import uuid



from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession



from app.core.config import get_settings
from app.db.session import get_db

from app.core.deps import require_student_actor

from app.models.user import User

from app.schemas.language_grammar_student import (

    GrammarActivityCompleteIn,

    GrammarActivityCompleteOut,

    GrammarDashboardOut,

    GrammarLessonOut,

    GrammarLessonStartIn,
    GrammarLessonChatCreateIn,
    GrammarLessonChatAudioIn,
    GrammarLessonChatAudioOut,
    GrammarLessonChatSendIn,
    GrammarLessonChatSendOut,
    GrammarLessonChatSessionOut,

    GrammarModuleStatusOut,
    GrammarPracticePreviewEvaluateIn,
    GrammarPracticePreviewEvaluateOut,

)

from app.services.language_access_service import require_language_learning_ready

from app.services.language_grammar_module import (

    build_grammar_dashboard,

    complete_grammar_activity,

    grammar_module_enabled,

    start_grammar_lesson,

)

from app.services.language_grammar_module.service import GrammarModuleError
from app.services.language_grammar_canonical_authoring.preview import (
    GrammarCanonicalPreviewError,
    build_canonical_revision_preview_lesson,
)
from app.services.language_grammar_canonical_authoring.practice_evaluation import (
    GrammarPracticeEvaluationError,
    evaluate_canonical_revision_preview_practice,
    evaluate_canonical_revision_student_practice,
)
from app.services.language_grammar_lesson_chat import (
    GrammarLessonChatError,
    close_preview_chat_session,
    close_student_chat_session,
    create_preview_chat_session,
    create_student_chat_session,
    get_safe_chat_history,
    send_preview_chat_message,
    send_student_chat_message,
    synthesize_preview_chat_message_audio,
    synthesize_student_chat_message_audio,
)



logger = logging.getLogger(__name__)



router = APIRouter(prefix="/student/grammar", tags=["Student Grammar"])


def _require_grammar_preview_enabled() -> None:
    settings = get_settings()
    if not settings.DEBUG or not settings.LANG_GRAMMAR_CANONICAL_PREVIEW_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grammar lesson preview is not available.")


def _parse_uuid(value: str, *, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field_name}.") from None


def _raise_chat_error(exc: GrammarLessonChatError) -> None:
    if exc.code in {"revision_not_found", "canonical_lesson_not_found", "session_not_found", "message_not_found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grammar chat was not found.") from None
    if exc.code in {"revision_not_reviewable", "revision_not_available", "revision_payload_invalid", "revision_mismatch", "session_closed"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from None
    if exc.code in {"message_too_long", "message_limit", "empty_message", "invalid_mode", "message_not_assistant", "no_speakable_text"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from None
    logger.warning("grammar_lesson_chat_failed code=%s", exc.code)
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Grammar chat is temporarily unavailable.") from None





@router.get("/status", response_model=GrammarModuleStatusOut)

async def grammar_module_status(

    _student: User = Depends(require_student_actor()),

):

    return GrammarModuleStatusOut(enabled=grammar_module_enabled())





@router.get("/dashboard", response_model=GrammarDashboardOut)

async def grammar_dashboard(

    student: User = Depends(require_language_learning_ready()),

    db: AsyncSession = Depends(get_db),

):

    if not grammar_module_enabled():

        return GrammarDashboardOut(enabled=False)

    try:

        data = await build_grammar_dashboard(db, student_id=student.id)

        return GrammarDashboardOut(**data)

    except Exception:  # noqa: BLE001

        logger.exception("grammar_dashboard_failed")

        raise HTTPException(

            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,

            detail="Grammar is temporarily unavailable. Please try again.",

        ) from None





@router.post("/lesson/start", response_model=GrammarLessonOut)

async def grammar_lesson_start(

    body: GrammarLessonStartIn | None = None,

    student: User = Depends(require_language_learning_ready()),

    db: AsyncSession = Depends(get_db),

):

    if not grammar_module_enabled():

        raise HTTPException(

            status_code=status.HTTP_404_NOT_FOUND,

            detail="Grammar module is not available.",

        )

    payload = body or GrammarLessonStartIn()

    try:

        lesson = await start_grammar_lesson(

            db,

            student_id=student.id,

            language_id=payload.language_id,

            use_llm_authoring=payload.use_llm_authoring,

            requested_grammar_id=payload.grammar_id,

        )

        return GrammarLessonOut(**lesson)

    except GrammarModuleError as exc:

        if exc.code == "module_disabled":

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grammar module is not available.") from None

        if exc.code == "no_grammar_target":

            raise HTTPException(

                status_code=status.HTTP_409_CONFLICT,

                detail="No grammar topic is ready yet. Complete language placement first.",

            ) from None

        logger.warning("grammar_lesson_start_failed code=%s", exc.code)

        raise HTTPException(

            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,

            detail="We couldn't generate your Grammar lesson. Please try again.",

        ) from None

    except Exception:  # noqa: BLE001

        logger.exception("grammar_lesson_start_unexpected")

        raise HTTPException(

            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,

            detail="We couldn't generate your Grammar lesson. Please try again.",

        ) from None





@router.get("/lesson/preview", response_model=GrammarLessonOut)
async def grammar_lesson_preview(
    revision_id: str,
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    if not settings.DEBUG or not settings.LANG_GRAMMAR_CANONICAL_PREVIEW_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grammar lesson preview is not available.")

    try:
        parsed_revision_id = uuid.UUID(str(revision_id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid revision_id.") from None

    try:
        lesson = await build_canonical_revision_preview_lesson(db, revision_id=parsed_revision_id)
        return GrammarLessonOut(**lesson)
    except GrammarCanonicalPreviewError as exc:
        if exc.code in {"revision_not_found", "canonical_lesson_not_found"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grammar lesson preview was not found.") from None
        if exc.code == "revision_not_reviewable":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This Grammar lesson revision is not ready for review.",
            ) from None
        logger.warning("grammar_lesson_preview_failed code=%s", exc.code)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This Grammar lesson revision cannot be previewed safely.",
        ) from None
    except Exception:  # noqa: BLE001
        logger.exception("grammar_lesson_preview_unexpected")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grammar lesson preview is temporarily unavailable.",
        ) from None


@router.post("/lesson/preview/practice/evaluate", response_model=GrammarPracticePreviewEvaluateOut)
async def grammar_lesson_preview_practice_evaluate(
    body: GrammarPracticePreviewEvaluateIn,
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    if not settings.DEBUG or not settings.LANG_GRAMMAR_CANONICAL_PREVIEW_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grammar lesson preview is not available.")

    try:
        parsed_revision_id = uuid.UUID(str(body.revision_id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid revision_id.") from None

    try:
        result = await evaluate_canonical_revision_preview_practice(
            db,
            revision_id=parsed_revision_id,
            item_id=body.item_id,
            learner_response=body.learner_response,
            attempt_number=body.attempt_number,
        )
        return GrammarPracticePreviewEvaluateOut(**result.to_dict())
    except GrammarPracticeEvaluationError as exc:
        if exc.code in {"revision_not_found", "canonical_lesson_not_found", "unknown_task_id"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice item was not found.") from None
        if exc.code == "revision_not_reviewable":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This Grammar lesson revision is not ready for practice preview.",
            ) from None
        logger.warning("grammar_lesson_preview_practice_evaluate_failed code=%s", exc.code)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This practice item cannot be evaluated safely.",
        ) from None
    except Exception:  # noqa: BLE001
        logger.exception("grammar_lesson_preview_practice_evaluate_unexpected")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Practice evaluation is temporarily unavailable.",
        ) from None


@router.post("/lesson/practice/evaluate", response_model=GrammarPracticePreviewEvaluateOut)
async def grammar_lesson_practice_evaluate(
    body: GrammarPracticePreviewEvaluateIn,
    _student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    try:
        parsed_revision_id = uuid.UUID(str(body.revision_id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid revision_id.") from None

    try:
        result = await evaluate_canonical_revision_student_practice(
            db,
            revision_id=parsed_revision_id,
            item_id=body.item_id,
            learner_response=body.learner_response,
            attempt_number=body.attempt_number,
            allow_reviewable=bool(get_settings().DEBUG),
        )
        return GrammarPracticePreviewEvaluateOut(**result.to_dict())
    except GrammarPracticeEvaluationError as exc:
        if exc.code in {"revision_not_found", "canonical_lesson_not_found", "unknown_task_id"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice item was not found.") from None
        if exc.code in {"revision_not_available", "revision_not_reviewable"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This Grammar lesson is not ready for practice.",
            ) from None
        logger.warning("grammar_lesson_practice_evaluate_failed code=%s", exc.code)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This practice item cannot be evaluated safely.",
        ) from None
    except Exception:  # noqa: BLE001
        logger.exception("grammar_lesson_practice_evaluate_unexpected")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Practice evaluation is temporarily unavailable.",
        ) from None


@router.post("/lesson/chat/sessions", response_model=GrammarLessonChatSessionOut)
async def grammar_lesson_chat_create(
    body: GrammarLessonChatCreateIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> GrammarLessonChatSessionOut:
    parsed_revision_id = _parse_uuid(body.revision_id, field_name="revision_id")
    try:
        result = await create_student_chat_session(db, revision_id=parsed_revision_id, user_id=student.id)
        await db.commit()
        return GrammarLessonChatSessionOut(**result)
    except GrammarLessonChatError as exc:
        await db.rollback()
        _raise_chat_error(exc)
        raise AssertionError("unreachable")
    except Exception:  # noqa: BLE001
        await db.rollback()
        logger.exception("grammar_lesson_chat_create_unexpected")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grammar chat is temporarily unavailable.",
        ) from None


@router.get("/lesson/chat/sessions/{session_id}", response_model=GrammarLessonChatSessionOut)
async def grammar_lesson_chat_history(
    session_id: str,
    revision_id: str | None = None,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> GrammarLessonChatSessionOut:
    parsed_session_id = _parse_uuid(session_id, field_name="session_id")
    parsed_revision_id = _parse_uuid(revision_id, field_name="revision_id") if revision_id else None
    try:
        result = await get_safe_chat_history(
            db,
            session_id=parsed_session_id,
            revision_id=parsed_revision_id,
            expected_mode="student",
            user_id=student.id,
        )
        return GrammarLessonChatSessionOut(**result)
    except GrammarLessonChatError as exc:
        _raise_chat_error(exc)
        raise AssertionError("unreachable")
    except Exception:  # noqa: BLE001
        logger.exception("grammar_lesson_chat_history_unexpected")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grammar chat is temporarily unavailable.",
        ) from None


@router.post("/lesson/chat/sessions/{session_id}/messages", response_model=GrammarLessonChatSendOut)
async def grammar_lesson_chat_send(
    session_id: str,
    body: GrammarLessonChatSendIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> GrammarLessonChatSendOut:
    parsed_session_id = _parse_uuid(session_id, field_name="session_id")
    parsed_revision_id = _parse_uuid(body.revision_id, field_name="revision_id") if body.revision_id else None
    try:
        result = await send_student_chat_message(
            db,
            session_id=parsed_session_id,
            revision_id=parsed_revision_id,
            message=body.message,
            section_key=body.section_key,
            block_context=body.block_context,
            user_id=student.id,
        )
        await db.commit()
        return GrammarLessonChatSendOut(**result)
    except GrammarLessonChatError as exc:
        await db.rollback()
        _raise_chat_error(exc)
        raise AssertionError("unreachable")
    except Exception:  # noqa: BLE001
        await db.rollback()
        logger.exception("grammar_lesson_chat_send_unexpected")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grammar chat is temporarily unavailable.",
        ) from None


@router.post(
    "/lesson/chat/sessions/{session_id}/messages/{message_id}/audio",
    response_model=GrammarLessonChatAudioOut,
)
async def grammar_lesson_chat_audio(
    session_id: str,
    message_id: str,
    body: GrammarLessonChatAudioIn | None = None,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> GrammarLessonChatAudioOut:
    payload = body or GrammarLessonChatAudioIn()
    parsed_session_id = _parse_uuid(session_id, field_name="session_id")
    parsed_message_id = _parse_uuid(message_id, field_name="message_id")
    parsed_revision_id = _parse_uuid(payload.revision_id, field_name="revision_id") if payload.revision_id else None
    try:
        result = await synthesize_student_chat_message_audio(
            db,
            session_id=parsed_session_id,
            message_id=parsed_message_id,
            revision_id=parsed_revision_id,
            user_id=student.id,
        )
        return GrammarLessonChatAudioOut(**result)
    except GrammarLessonChatError as exc:
        _raise_chat_error(exc)
        raise AssertionError("unreachable")
    except Exception:  # noqa: BLE001
        logger.exception("grammar_lesson_chat_audio_unexpected")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grammar chat voice is temporarily unavailable.",
        ) from None


@router.post("/lesson/chat/sessions/{session_id}/close", response_model=GrammarLessonChatSessionOut)
async def grammar_lesson_chat_close(
    session_id: str,
    revision_id: str | None = None,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
) -> GrammarLessonChatSessionOut:
    parsed_session_id = _parse_uuid(session_id, field_name="session_id")
    parsed_revision_id = _parse_uuid(revision_id, field_name="revision_id") if revision_id else None
    try:
        result = await close_student_chat_session(
            db,
            session_id=parsed_session_id,
            revision_id=parsed_revision_id,
            user_id=student.id,
        )
        await db.commit()
        return GrammarLessonChatSessionOut(**result)
    except GrammarLessonChatError as exc:
        await db.rollback()
        _raise_chat_error(exc)
        raise AssertionError("unreachable")
    except Exception:  # noqa: BLE001
        await db.rollback()
        logger.exception("grammar_lesson_chat_close_unexpected")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grammar chat is temporarily unavailable.",
        ) from None


@router.post("/lesson/preview/chat/sessions", response_model=GrammarLessonChatSessionOut)
async def grammar_lesson_preview_chat_create(
    body: GrammarLessonChatCreateIn,
    db: AsyncSession = Depends(get_db),
) -> GrammarLessonChatSessionOut:
    _require_grammar_preview_enabled()
    parsed_revision_id = _parse_uuid(body.revision_id, field_name="revision_id")
    try:
        result = await create_preview_chat_session(db, revision_id=parsed_revision_id)
        await db.commit()
        return GrammarLessonChatSessionOut(**result)
    except GrammarLessonChatError as exc:
        await db.rollback()
        _raise_chat_error(exc)
        raise AssertionError("unreachable")
    except Exception:  # noqa: BLE001
        await db.rollback()
        logger.exception("grammar_lesson_preview_chat_create_unexpected")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grammar chat is temporarily unavailable.",
        ) from None


@router.get("/lesson/preview/chat/sessions/{session_id}", response_model=GrammarLessonChatSessionOut)
async def grammar_lesson_preview_chat_history(
    session_id: str,
    revision_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> GrammarLessonChatSessionOut:
    _require_grammar_preview_enabled()
    parsed_session_id = _parse_uuid(session_id, field_name="session_id")
    parsed_revision_id = _parse_uuid(revision_id, field_name="revision_id") if revision_id else None
    try:
        result = await get_safe_chat_history(db, session_id=parsed_session_id, revision_id=parsed_revision_id)
        return GrammarLessonChatSessionOut(**result)
    except GrammarLessonChatError as exc:
        _raise_chat_error(exc)
        raise AssertionError("unreachable")
    except Exception:  # noqa: BLE001
        logger.exception("grammar_lesson_preview_chat_history_unexpected")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grammar chat is temporarily unavailable.",
        ) from None


@router.post("/lesson/preview/chat/sessions/{session_id}/messages", response_model=GrammarLessonChatSendOut)
async def grammar_lesson_preview_chat_send(
    session_id: str,
    body: GrammarLessonChatSendIn,
    db: AsyncSession = Depends(get_db),
) -> GrammarLessonChatSendOut:
    _require_grammar_preview_enabled()
    parsed_session_id = _parse_uuid(session_id, field_name="session_id")
    parsed_revision_id = _parse_uuid(body.revision_id, field_name="revision_id") if body.revision_id else None
    try:
        result = await send_preview_chat_message(
            db,
            session_id=parsed_session_id,
            revision_id=parsed_revision_id,
            message=body.message,
            section_key=body.section_key,
            block_context=body.block_context,
        )
        await db.commit()
        return GrammarLessonChatSendOut(**result)
    except GrammarLessonChatError as exc:
        await db.rollback()
        _raise_chat_error(exc)
        raise AssertionError("unreachable")
    except Exception:  # noqa: BLE001
        await db.rollback()
        logger.exception("grammar_lesson_preview_chat_send_unexpected")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grammar chat is temporarily unavailable.",
        ) from None


@router.post(
    "/lesson/preview/chat/sessions/{session_id}/messages/{message_id}/audio",
    response_model=GrammarLessonChatAudioOut,
)
async def grammar_lesson_preview_chat_audio(
    session_id: str,
    message_id: str,
    body: GrammarLessonChatAudioIn | None = None,
    db: AsyncSession = Depends(get_db),
) -> GrammarLessonChatAudioOut:
    _require_grammar_preview_enabled()
    payload = body or GrammarLessonChatAudioIn()
    parsed_session_id = _parse_uuid(session_id, field_name="session_id")
    parsed_message_id = _parse_uuid(message_id, field_name="message_id")
    parsed_revision_id = _parse_uuid(payload.revision_id, field_name="revision_id") if payload.revision_id else None
    try:
        result = await synthesize_preview_chat_message_audio(
            db,
            session_id=parsed_session_id,
            message_id=parsed_message_id,
            revision_id=parsed_revision_id,
        )
        return GrammarLessonChatAudioOut(**result)
    except GrammarLessonChatError as exc:
        _raise_chat_error(exc)
        raise AssertionError("unreachable")
    except Exception:  # noqa: BLE001
        logger.exception("grammar_lesson_preview_chat_audio_unexpected")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grammar chat voice is temporarily unavailable.",
        ) from None


@router.post("/lesson/preview/chat/sessions/{session_id}/close", response_model=GrammarLessonChatSessionOut)
async def grammar_lesson_preview_chat_close(
    session_id: str,
    revision_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> GrammarLessonChatSessionOut:
    _require_grammar_preview_enabled()
    parsed_session_id = _parse_uuid(session_id, field_name="session_id")
    parsed_revision_id = _parse_uuid(revision_id, field_name="revision_id") if revision_id else None
    try:
        result = await close_preview_chat_session(db, session_id=parsed_session_id, revision_id=parsed_revision_id)
        await db.commit()
        return GrammarLessonChatSessionOut(**result)
    except GrammarLessonChatError as exc:
        await db.rollback()
        _raise_chat_error(exc)
        raise AssertionError("unreachable")
    except Exception:  # noqa: BLE001
        await db.rollback()
        logger.exception("grammar_lesson_preview_chat_close_unexpected")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grammar chat is temporarily unavailable.",
        ) from None


@router.post("/activity/complete", response_model=GrammarActivityCompleteOut)

async def grammar_activity_complete(

    body: GrammarActivityCompleteIn,

    student: User = Depends(require_language_learning_ready()),

    db: AsyncSession = Depends(get_db),

):

    """Wave D — attested completion; client may not send grammar_id or score."""

    if not grammar_module_enabled():

        raise HTTPException(

            status_code=status.HTTP_404_NOT_FOUND,

            detail="Grammar module is not available.",

        )

    try:

        result = await complete_grammar_activity(

            db,

            student_id=student.id,

            language_id=body.language_id,

            activity_session_id=body.activity_session_id,

            answers=body.answers,

            response_text=body.response_text,

        )

        return GrammarActivityCompleteOut(**result)

    except GrammarModuleError as exc:

        if exc.code == "module_disabled":

            raise HTTPException(

                status_code=status.HTTP_404_NOT_FOUND,

                detail="Grammar module is not available.",

            ) from None

        if exc.code in {
            "grammar_practice_answers_required",
            "grammar_practice_key_unavailable",
            "grammar_practice_not_complete",
        }:

            raise HTTPException(

                status_code=status.HTTP_409_CONFLICT,

                detail="Complete all 14 Grammar practice items correctly before finishing.",

            ) from None

        if exc.code in {
            "invalid_skill",
            "invalid_evidence",
            "invalid_student",
            "stamp_forged",
            "student_ownership",
            "session_not_found",
            "session_not_open",
            "session_expired",
            "duplicate_observation",
            "invalid_session_id",
            "score_unavailable",
            "stamp_student_mismatch",
            "stamp_grammar_mismatch",
            "stamp_session_mismatch",
        }:

            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from None

        logger.warning("grammar_activity_complete_failed code=%s", exc.code)

        raise HTTPException(

            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,

            detail="We couldn't record your Grammar progress. Please try again.",

        ) from None

    except Exception:  # noqa: BLE001

        logger.exception("grammar_activity_complete_unexpected")

        raise HTTPException(

            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,

            detail="We couldn't record your Grammar progress. Please try again.",

        ) from None
