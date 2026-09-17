"""Whisper rollback provider for uploaded lesson videos only."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from app.core.config import get_settings
from app.services.video_transcription.base import TranscriptionProvider
from app.services.video_transcription.errors import (
    CATEGORY_EMPTY_AUDIO,
    CATEGORY_EMPTY_TRANSCRIPT,
    CATEGORY_PROVIDER_CONFIG,
    VideoTranscriptionError,
    user_message_for,
)
from app.services.video_transcription.types import TranscriptResult

logger = logging.getLogger(__name__)


class WhisperTranscriptionProvider(TranscriptionProvider):
    """Faster-whisper rollback for lesson video when explicitly selected/allowed."""

    @property
    def name(self) -> str:
        return "whisper"

    async def transcribe(
        self,
        audio_path: Path,
        *,
        language: str,
        mime_type: str | None = None,
        keyterms: list[str] | None = None,
    ) -> TranscriptResult:
        _ = mime_type, keyterms
        return await asyncio.to_thread(self._transcribe_sync, audio_path, language=language)

    def _transcribe_sync(self, audio_path: Path, *, language: str) -> TranscriptResult:
        settings = get_settings()
        if not settings.ENABLE_WHISPER:
            raise VideoTranscriptionError(
                user_message_for(CATEGORY_PROVIDER_CONFIG),
                category=CATEGORY_PROVIDER_CONFIG,
                provider=self.name,
            )
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise VideoTranscriptionError(
                user_message_for(CATEGORY_EMPTY_AUDIO),
                category=CATEGORY_EMPTY_AUDIO,
                provider=self.name,
            )

        started = time.perf_counter()
        # Lazy import keeps Deepgram-only deploys from requiring Whisper at import time
        # beyond what voice_service already uses for other flows.
        from app.services import voice_service

        # Map Deepgram-style codes to Whisper language codes.
        whisper_language = language
        if language.lower() in {"ar-sy", "ar_sy"} or language.lower().startswith("ar"):
            whisper_language = "ar"
        elif language.lower().startswith("en"):
            whisper_language = "en"

        try:
            model = voice_service._get_lesson_faster_whisper_model()
            segments, _info = model.transcribe(
                str(audio_path),
                language=whisper_language,
                beam_size=5,
                vad_filter=False,
            )
            text = "".join(s.text for s in segments).strip()
        except Exception as exc:
            logger.warning("Whisper lesson video transcription failed: %s", type(exc).__name__)
            raise VideoTranscriptionError(
                user_message_for(CATEGORY_EMPTY_TRANSCRIPT),
                category=CATEGORY_EMPTY_TRANSCRIPT,
                provider=self.name,
            ) from exc

        if not text:
            raise VideoTranscriptionError(
                user_message_for(CATEGORY_EMPTY_TRANSCRIPT),
                category=CATEGORY_EMPTY_TRANSCRIPT,
                provider=self.name,
            )

        model_id = voice_service._lesson_faster_whisper_model_id()
        logger.info(
            "Lesson video STT provider=whisper model=%s language=%s processing_duration_s=%.2f chars=%s",
            model_id,
            whisper_language,
            time.perf_counter() - started,
            len(text),
        )
        return TranscriptResult(
            text=text,
            provider="whisper",
            model=model_id,
            language=whisper_language,
            duration_s=time.perf_counter() - started,
            status="ok",
        )
