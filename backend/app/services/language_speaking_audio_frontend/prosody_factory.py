"""Prosody provider factory (S6) — no silent fallback."""

from __future__ import annotations

from app.core.config import get_settings
from app.services.language_speaking_audio_frontend.errors import ProsodyProviderUnavailableError
from app.services.language_speaking_providers.prosody_acoustic import AcousticProsodyProvider
from app.services.language_speaking_providers.prosody_hume import HumeProsodyProvider
from app.services.language_speaking_providers.prosody_mock import MockProsodyProvider
from app.services.language_speaking_providers.providers import AcousticFeatureProvider

settings = get_settings()

# Production default is the numpy-derived acoustic provider. The Hume
# Expression Measurement API was discontinued by the vendor (2026-06-14); it
# remains registered only so its call path raises a structured discontinued
# error rather than silently succeeding.
_SUPPORTED_PROVIDERS: dict[str, type[AcousticFeatureProvider]] = {
    "acoustic": AcousticProsodyProvider,
    "hume": HumeProsodyProvider,
    "mock": MockProsodyProvider,
}

_DEFAULT_PROVIDER = "acoustic"


def supported_prosody_providers() -> frozenset[str]:
    return frozenset(_SUPPORTED_PROVIDERS.keys())


def build_prosody_provider(name: str | None = None) -> AcousticFeatureProvider:
    """Return a configured prosody provider. Raises on unknown/unavailable."""
    provider_name = (name or settings.SPEAKING_PROSODY_PROVIDER or _DEFAULT_PROVIDER).strip().lower()
    if provider_name not in _SUPPORTED_PROVIDERS:
        raise ProsodyProviderUnavailableError(
            f"Unknown prosody provider: {provider_name}",
            detail=f"supported={sorted(_SUPPORTED_PROVIDERS.keys())}",
        )
    if provider_name == "acoustic":
        try:
            import numpy  # noqa: F401
        except ImportError as exc:
            raise ProsodyProviderUnavailableError(
                "Acoustic prosody provider requires numpy",
                detail=str(exc),
            ) from exc
    if provider_name == "hume":
        api_key = (settings.HUME_API_KEY or "").strip()
        if not api_key:
            raise ProsodyProviderUnavailableError(
                "Hume prosody provider requires HUME_API_KEY",
                detail="missing_api_key",
            )
        try:
            import httpx  # noqa: F401
        except ImportError as exc:
            raise ProsodyProviderUnavailableError(
                "Hume prosody provider requires httpx",
                detail=str(exc),
            ) from exc
    return _SUPPORTED_PROVIDERS[provider_name]()
