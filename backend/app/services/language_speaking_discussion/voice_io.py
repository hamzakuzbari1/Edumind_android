"""Guided Discussion voice I/O — GPT STT/TTS only (no reasoning).

Reuses shared infrastructure from language_speaking_audio_frontend:
- TTS: tts_runtime.synthesize_spoken_line
- STT: normalize + transcription provider

Never imports Scene Director, rehearsal, LiveBridge engine, or Alex.
"""

from __future__ import annotations

import base64
import logging
import uuid
from typing import Any

from app.services.language_speaking_audio_frontend.errors import SpeakingAudioRuntimeError
from app.services.language_speaking_audio_frontend.media_adapter import artifact_from_bytes
from app.services.language_speaking_audio_frontend.normalization_runtime import (
    normalize_audio_with_bytes,
)
from app.services.language_speaking_audio_frontend.transcription_factory import (
    build_transcription_provider,
)
from app.services.language_speaking_audio_frontend.tts_runtime import synthesize_spoken_line
from app.services.language_transcription_service import transcribe_english_audio

logger = logging.getLogger(__name__)


class DiscussionVoiceError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _suffix_for_mime(mime_type: str) -> str:
    mime = (mime_type or "").split(";")[0].strip().lower()
    if mime in {"audio/wav", "audio/x-wav"}:
        return ".wav"
    if mime == "audio/ogg":
        return ".ogg"
    if mime in {"audio/mp4", "video/mp4"}:
        return ".m4a"
    if mime == "audio/mpeg":
        return ".mp3"
    return ".webm"


async def transcribe_discussion_audio(
    audio_bytes: bytes,
    mime_type: str,
    *,
    student_id: int,
    language_id: int,
) -> tuple[str, float | None]:
    """GPT STT for one discussion turn. Raises DiscussionVoiceError on hard failure."""
    if not audio_bytes:
        raise DiscussionVoiceError("empty_audio", "No audio received.")

    artifact = artifact_from_bytes(
        audio_id=f"disc_{uuid.uuid4().hex[:10]}",
        session_id="guided_discussion",
        student_id=student_id,
        language_id=language_id,
        audio_bytes=audio_bytes,
        original_filename="discussion_turn",
        content_type=(mime_type or "audio/webm").split(";")[0].strip().lower(),
    )
    try:
        _normalized, wav_bytes, _warnings = normalize_audio_with_bytes(artifact, audio_bytes)
    except SpeakingAudioRuntimeError as exc:
        if (mime_type or "").lower().startswith(("audio/wav", "audio/x-wav")):
            wav_bytes = audio_bytes
        else:
            raise DiscussionVoiceError(
                "stt_unavailable", "Could not process your recording."
            ) from exc

    result: dict | None = None
    last_exc: Exception | None = None
    try:
        provider = build_transcription_provider()
        result = await provider.transcribe(
            audio_bytes=wav_bytes,
            mime_type="audio/wav",
            language="en",
            initial_prompt="",
        )
    except Exception as exc:  # noqa: BLE001
        last_exc = exc
        logger.warning(
            "Discussion configured STT provider failed; trying shared language STT",
            exc_info=True,
        )

    if result is None:
        logger.warning(
            "Discussion dedicated STT failed; trying shared language STT",
            exc_info=last_exc,
        )
        try:
            shared = await transcribe_english_audio(
                audio_bytes,
                suffix=_suffix_for_mime(mime_type),
            )
            shared_text = str(getattr(shared, "text", "") or "").strip()
            if shared_text:
                return shared_text, None
        except Exception:  # noqa: BLE001 - voice retry must not expose provider internals
            logger.warning("Discussion shared language STT fallback failed", exc_info=True)
        logger.warning("Discussion STT produced no usable transcript; returning gentle retry")
        return "", None

    transcript = str(result.get("text") or "").strip()
    confidence_raw = result.get("provider_confidence")
    confidence = float(confidence_raw) if isinstance(confidence_raw, (int, float)) else None
    return transcript, confidence


async def tts_discussion_line(text: str) -> dict[str, Any]:
    """Tutor line TTS (Supertonic preferred, OpenAI fallback). Never load-bearing."""
    synthesized = await synthesize_spoken_line(text)
    if synthesized is None:
        return {"audio_b64": None, "audio_mime": None}
    audio, mime = synthesized
    return {
        "audio_b64": base64.b64encode(audio).decode("ascii"),
        "audio_mime": mime,
    }
