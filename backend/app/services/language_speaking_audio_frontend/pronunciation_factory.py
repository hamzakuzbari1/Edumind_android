"""Pronunciation provider factory (S5) — no silent fallback."""

from __future__ import annotations

from app.core.config import get_settings
from app.services.language_speaking_audio_frontend.errors import PronunciationProviderUnavailableError
from app.services.language_speaking_providers.pronunciation_mock import MockPronunciationProvider
from app.services.language_speaking_providers.pronunciation_wav2vec2 import RealPronunciationProvider
from app.services.language_speaking_providers.providers import PhonemeAlignmentProvider

settings = get_settings()

_SUPPORTED_PROVIDERS: dict[str, type[PhonemeAlignmentProvider]] = {
    "wav2vec2": RealPronunciationProvider,
    "mock": MockPronunciationProvider,
}

_DEFAULT_PROVIDER = "wav2vec2"


def supported_pronunciation_providers() -> frozenset[str]:
    return frozenset(_SUPPORTED_PROVIDERS.keys())


def build_pronunciation_provider(name: str | None = None) -> PhonemeAlignmentProvider:
    """Return a configured pronunciation provider. Raises on unknown/unavailable."""
    provider_name = (name or settings.SPEAKING_PRONUNCIATION_PROVIDER or _DEFAULT_PROVIDER).strip().lower()
    if provider_name not in _SUPPORTED_PROVIDERS:
        raise PronunciationProviderUnavailableError(
            f"Unknown pronunciation provider: {provider_name}",
            detail=f"supported={sorted(_SUPPORTED_PROVIDERS.keys())}",
        )
    if provider_name == "wav2vec2":
        try:
            import transformers  # noqa: F401
            import torch  # noqa: F401
        except ImportError as exc:
            raise PronunciationProviderUnavailableError(
                "wav2vec2 pronunciation provider requires torch and transformers",
                detail=str(exc),
            ) from exc
        try:
            import phonemizer  # noqa: F401
        except ImportError as exc:
            raise PronunciationProviderUnavailableError(
                "wav2vec2 pronunciation provider requires phonemizer",
                detail=str(exc),
            ) from exc
    return _SUPPORTED_PROVIDERS[provider_name]()
