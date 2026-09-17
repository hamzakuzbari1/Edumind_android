"""Provider-neutral ABC for uploaded lesson-video transcription."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.services.video_transcription.types import TranscriptResult


class TranscriptionProvider(ABC):
    """Transcribe extracted lesson-video audio to text."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def transcribe(
        self,
        audio_path: Path,
        *,
        language: str,
        mime_type: str | None = None,
        keyterms: list[str] | None = None,
    ) -> TranscriptResult:
        """Transcribe local audio bytes. Must not log secrets or raw responses."""
