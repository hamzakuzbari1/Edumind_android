"""Factory for uploaded lesson-video transcription providers."""

from __future__ import annotations

from app.core.config import get_settings
from app.services.video_transcription.base import TranscriptionProvider
from app.services.video_transcription.deepgram import DeepgramTranscriptionProvider
from app.services.video_transcription.errors import (
    CATEGORY_PROVIDER_CONFIG,
    VideoTranscriptionError,
    user_message_for,
)
from app.services.video_transcription.whisper import WhisperTranscriptionProvider


def get_video_transcription_provider(name: str | None = None) -> TranscriptionProvider:
    settings = get_settings()
    provider_name = (name or settings.VIDEO_TRANSCRIPTION_PROVIDER or "deepgram").strip().lower()
    if provider_name in {"deepgram", "nova", "nova-3"}:
        return DeepgramTranscriptionProvider()
    if provider_name in {"whisper", "faster-whisper", "faster_whisper"}:
        return WhisperTranscriptionProvider()
    raise VideoTranscriptionError(
        user_message_for(CATEGORY_PROVIDER_CONFIG),
        category=CATEGORY_PROVIDER_CONFIG,
        provider=provider_name,
    )
