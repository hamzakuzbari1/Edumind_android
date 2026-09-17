"""Uploaded lesson-video transcription providers (Deepgram / Whisper).

This package is scoped to teacher lesson video → transcript only.
It does not replace Language Speaking STT, placement Speaking, teacher voice
samples, or student chat STT.
"""

from app.services.video_transcription.base import TranscriptionProvider
from app.services.video_transcription.errors import VideoTranscriptionError
from app.services.video_transcription.factory import get_video_transcription_provider
from app.services.video_transcription.types import TranscriptResult

__all__ = [
    "TranscriptionProvider",
    "TranscriptResult",
    "VideoTranscriptionError",
    "get_video_transcription_provider",
]
