"""Background TTS for student chat — decoupled from the HTTP request."""

from __future__ import annotations

import asyncio
import json
import logging
import time

from app.core.config import get_settings
from app.models.chat import ChatMessage
from app.services.tts_service import prepare_synthesis_text, synthesize_answer_audio

logger = logging.getLogger(__name__)
settings = get_settings()

SOURCE_MARKER = "\n\n[[EDUSPARK_SOURCES:"
SOURCE_MARKER_END = "]]"
AUDIO_MARKER = "\n\n[[EDUSPARK_AUDIO:"
AUDIO_MARKER_END = "]]"
VISUAL_MARKER = "\n\n[[EDUSPARK_VISUAL:"
VISUAL_MARKER_END = "]]"


def _pack_ai_content(
    reply: str,
    sources: list[dict],
    audio_url: str | None = None,
    visual: dict | None = None,
) -> str:
    content = reply
    if sources:
        payload = json.dumps(sources, ensure_ascii=False)
        content = f"{content}{SOURCE_MARKER}{payload}{SOURCE_MARKER_END}"
    if audio_url:
        payload = json.dumps({"audioUrl": audio_url}, ensure_ascii=False)
        content = f"{content}{AUDIO_MARKER}{payload}{AUDIO_MARKER_END}"
    if visual:
        payload = json.dumps(visual, ensure_ascii=False)
        content = f"{content}{VISUAL_MARKER}{payload}{VISUAL_MARKER_END}"
    return content


async def _run_chat_answer_audio(
    *,
    ai_message_id: int,
    reply: str,
    sources: list[dict],
    speaker_wav: str | None,
    elevenlabs_voice_id: str | None,
    lesson_id: int,
    visual: dict | None = None,
) -> None:
    from app.db.session import AsyncSessionLocal

    if not settings.ENABLE_TTS or not reply.strip():
        return

    tts_text = prepare_synthesis_text(reply)
    if not tts_text:
        logger.info(
            "chat_tts_skipped message_id=%s lesson_id=%s reason=empty_text_after_prepare",
            ai_message_id,
            lesson_id,
        )
        return

    started = time.perf_counter()
    logger.info(
        "chat_tts_start message_id=%s lesson_id=%s chars=%s",
        ai_message_id,
        lesson_id,
        len(tts_text),
    )

    try:
        audio_url = await synthesize_answer_audio(
            tts_text,
            speaker_wav,
            lesson_id,
            voice_id=elevenlabs_voice_id,
        )
        duration_s = time.perf_counter() - started
        if not audio_url:
            logger.warning(
                "chat_tts_failure message_id=%s lesson_id=%s duration_s=%.2f reason=no_audio_url",
                ai_message_id,
                lesson_id,
                duration_s,
            )
            return

        async with AsyncSessionLocal() as db:
            msg = await db.get(ChatMessage, ai_message_id)
            if not msg:
                logger.warning(
                    "chat_tts_failure message_id=%s lesson_id=%s duration_s=%.2f reason=message_not_found",
                    ai_message_id,
                    lesson_id,
                    duration_s,
                )
                return
            msg.content = _pack_ai_content(reply, sources, audio_url, visual=visual)
            await db.commit()

        logger.info(
            "chat_tts_success message_id=%s lesson_id=%s duration_s=%.2f audio_url=%s",
            ai_message_id,
            lesson_id,
            duration_s,
            audio_url,
        )
    except Exception as exc:
        duration_s = time.perf_counter() - started
        logger.warning(
            "chat_tts_failure message_id=%s lesson_id=%s duration_s=%.2f error=%s",
            ai_message_id,
            lesson_id,
            duration_s,
            exc,
        )


def schedule_chat_answer_audio(
    *,
    ai_message_id: int,
    reply: str,
    sources: list[dict],
    speaker_wav: str | None,
    elevenlabs_voice_id: str | None = None,
    lesson_id: int,
    visual: dict | None = None,
) -> None:
    asyncio.create_task(
        _run_chat_answer_audio(
            ai_message_id=ai_message_id,
            reply=reply,
            sources=sources,
            speaker_wav=speaker_wav,
            elevenlabs_voice_id=elevenlabs_voice_id,
            lesson_id=lesson_id,
            visual=visual,
        )
    )
