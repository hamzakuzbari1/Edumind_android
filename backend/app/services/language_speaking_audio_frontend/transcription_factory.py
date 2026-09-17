"""Transcription provider factory (S4) — no silent fallback."""

from __future__ import annotations

from app.core.config import get_settings
from app.services.language_speaking_audio_frontend.errors import TranscriptionProviderUnavailableError
from app.services.language_speaking_providers.providers import SpeechTranscriptionProvider
from app.services.language_speaking_providers.transcription_mock import MockTranscriptionProvider
from app.services.language_speaking_providers.transcription_openai import GPT4oTranscriptionProvider
from app.services.language_speaking_providers.transcription_whisper import FasterWhisperTranscriptionProvider

settings = get_settings()

# Production/default = "openai" (GPT-4o). faster_whisper = optional offline. mock = QA-only.
_SUPPORTED_PROVIDERS: dict[str, type[SpeechTranscriptionProvider]] = {
    "openai": GPT4oTranscriptionProvider,
    "faster_whisper": FasterWhisperTranscriptionProvider,
    "mock": MockTranscriptionProvider,
}

_DEFAULT_PROVIDER = "openai"


def supported_transcription_providers() -> frozenset[str]:
    return frozenset(_SUPPORTED_PROVIDERS.keys())


def build_transcription_provider(name: str | None = None) -> SpeechTranscriptionProvider:
    """Return a configured transcription provider. Raises on unknown/unavailable.

    There is NO silent fallback: an unavailable provider raises rather than
    switching to a different one.
    """
    provider_name = (name or settings.SPEAKING_TRANSCRIPTION_PROVIDER or _DEFAULT_PROVIDER).strip().lower()
    if provider_name not in _SUPPORTED_PROVIDERS:
        raise TranscriptionProviderUnavailableError(
            f"Unknown transcription provider: {provider_name}",
            detail=f"supported={sorted(_SUPPORTED_PROVIDERS.keys())}",
        )
    if provider_name == "openai":
        if not (settings.OPENAI_API_KEY or "").strip():
            raise TranscriptionProviderUnavailableError(
                "OpenAI transcription provider selected but OPENAI_API_KEY is not configured",
                detail="set OPENAI_API_KEY or select an explicit alternate provider",
            )
    if provider_name == "faster_whisper":
        try:
            import faster_whisper  # noqa: F401
        except ImportError as exc:
            raise TranscriptionProviderUnavailableError(
                "faster_whisper package not installed",
                detail=str(exc),
            ) from exc
    return _SUPPORTED_PROVIDERS[provider_name]()
