"""Mock SpeechTranscriptionProvider for S4 verification (deterministic, no SDK)."""

from __future__ import annotations

from app.services.language_speaking_providers.capabilities import TranscriptionCapabilities
from app.services.language_speaking_providers.providers import SpeechTranscriptionProvider


class MockTranscriptionProvider(SpeechTranscriptionProvider):
    """Deterministic transcript with segment + word timestamps for tests."""

    def capabilities(self) -> TranscriptionCapabilities:
        return TranscriptionCapabilities(
            supports_word_timestamps=True,
            supports_confidence_scores=True,
            supports_streaming=False,
            supported_languages=("en",),
            provider_name="mock",
        )

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
        language: str = "en",
        initial_prompt: str = "",
    ) -> dict[str, object]:
        if not audio_bytes:
            return {
                "text": "",
                "language": language,
                "provider_confidence": 0.0,
                "segments": [],
                "words": [],
                "model": "mock-v1",
                "provider_name": "mock",
            }
        return {
            "text": "hello world",
            "language": language,
            "provider_confidence": 0.95,
            "segments": [
                {"text": "hello world", "start_sec": 0.0, "end_sec": 0.9, "confidence": 0.95},
            ],
            "words": [
                {"word": "hello", "start_sec": 0.0, "end_sec": 0.4, "confidence": 0.96},
                {"word": "world", "start_sec": 0.5, "end_sec": 0.9, "confidence": 0.94},
            ],
            "model": "mock-v1",
            "provider_name": "mock",
            "provider_version": "0.1.0",
            "processing_version": "s4_mock",
        }
