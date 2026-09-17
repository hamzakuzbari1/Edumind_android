"""Orchestrate listening lesson acquisition — never surface HTTP 404 for normal waiting."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.language_listening_acquisition import (
    ListeningAcquisitionStatusOut,
    ListeningNextResponseOut,
)
from app.schemas.language_listening_bundles import LessonExperienceBundleOut
from app.services.language_generation_gate import can_generate, seconds_until_retry
from app.services.language_listening_service import (
    _active_unseen_count,
    _adaptive_level,
    next_listening,
)
from app.services.language_listening_reservation import listening_session_reservation_service
from app.services.language_subscription_service import get_default_language

logger = logging.getLogger(__name__)

MSG_PREFIX = "student.languages.listeningJourney.acquisition"


async def acquire_next_listening(
    db: AsyncSession,
    *,
    student_id: int,
    attempt: int = 1,
) -> tuple[ListeningNextResponseOut, bool]:
    """Return lesson bundle or explicit acquisition status. Second value = schedule background prefill."""
    language = await get_default_language(db)
    level = await _adaptive_level(db, student_id=student_id, language_id=language.id)

    lesson, schedule_prefill = await next_listening(db, student_id=student_id)

    if lesson:
        bundle = LessonExperienceBundleOut.model_validate(lesson)
        playback = bundle.playback
        if not playback.audio_available or not playback.audio_url:
            reserved_id = await listening_session_reservation_service.load_reserved_content_id(
                db, student_id=student_id, language_id=language.id
            )
            acquisition = ListeningAcquisitionStatusOut(
                status="generating",
                lesson_ready=False,
                waiting=True,
                generation_in_progress=True,
                temporary_failure=False,
                retry_after=None,
                queue_position=1,
                poll_after=3,
                reservation_id=str(reserved_id) if reserved_id else None,
                message_key=f"{MSG_PREFIX}.preparing",
                attempt=max(1, attempt),
                acquisition_id=str(uuid.uuid4()),
            )
            logger.info(
                "Listening acquisition waiting for audio student=%s lesson_id=%s attempt=%s",
                student_id,
                bundle.lesson_id,
                attempt,
            )
            return (
                ListeningNextResponseOut(outcome="acquisition_pending", acquisition=acquisition),
                True,
            )
        return (
            ListeningNextResponseOut(outcome="lesson_ready", bundle=bundle),
            schedule_prefill,
        )

    active_unseen = await _active_unseen_count(
        db, student_id=student_id, language_id=language.id, level=level
    )
    reserved_id = await listening_session_reservation_service.load_reserved_content_id(
        db, student_id=student_id, language_id=language.id
    )

    status, message_key, retry_after = _classify_pending(
        active_unseen=active_unseen,
        attempt=attempt,
        has_reservation=reserved_id is not None,
    )

    acquisition = ListeningAcquisitionStatusOut(
        status=status,
        lesson_ready=False,
        waiting=status in ("waiting", "generating", "retrying"),
        generation_in_progress=status in ("generating", "retrying"),
        temporary_failure=status == "temporary_failure",
        retry_after=retry_after,
        queue_position=1 if status in ("waiting", "generating", "retrying") else None,
        poll_after=_poll_after(status, retry_after),
        reservation_id=str(reserved_id) if reserved_id else None,
        message_key=message_key,
        attempt=max(1, attempt),
        acquisition_id=str(uuid.uuid4()),
    )

    logger.info(
        "Listening acquisition pending student=%s status=%s attempt=%s active_unseen=%s",
        student_id,
        status,
        attempt,
        active_unseen,
    )

    return (
        ListeningNextResponseOut(outcome="acquisition_pending", acquisition=acquisition),
        True,
    )


def _classify_pending(
    *,
    active_unseen: int,
    attempt: int,
    has_reservation: bool,
) -> tuple[str, str, int | None]:
    """Map pool/generation state to acquisition status + i18n key."""
    if not can_generate():
        retry = int(seconds_until_retry())
        return (
            "temporary_failure",
            f"{MSG_PREFIX}.unavailable",
            max(retry, 1),
        )

    if has_reservation and active_unseen == 0:
        return (
            "generating",
            f"{MSG_PREFIX}.preparing",
            None,
        )

    if active_unseen == 0:
        if attempt <= 1:
            return (
                "generating",
                f"{MSG_PREFIX}.preparing",
                None,
            )
        if attempt <= 4:
            return (
                "waiting",
                f"{MSG_PREFIX}.almostReady",
                None,
            )
        return (
            "temporary_failure",
            f"{MSG_PREFIX}.unavailable",
            60,
        )

    return (
        "waiting",
        f"{MSG_PREFIX}.finding",
        None,
    )


def _poll_after(status: str, retry_after: int | None) -> int:
    if status == "temporary_failure":
        return max(min(retry_after or 60, 120), 15)
    if status == "generating":
        return 3
    return 5
