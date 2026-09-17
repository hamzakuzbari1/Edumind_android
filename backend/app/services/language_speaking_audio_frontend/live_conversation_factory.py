"""Live conversation provider factory (S7.5) — no silent fallback."""

from __future__ import annotations

from app.core.config import get_settings
from app.services.language_speaking_providers.live_provider_errors import ProviderLiveUnavailableError
from app.services.language_speaking_providers.live_conversation_hume import HumeEviLiveConversationProvider
from app.services.language_speaking_providers.live_conversation_mock import MockEviLiveConversationProvider
from app.services.language_speaking_providers.providers import LiveConversationProvider

_SUPPORTED = {
    "hume_evi": HumeEviLiveConversationProvider,
    "mock": MockEviLiveConversationProvider,
}


def supported_live_conversation_providers() -> tuple[str, ...]:
    return tuple(sorted(_SUPPORTED))


def build_live_conversation_provider(name: str | None = None) -> LiveConversationProvider:
    settings = get_settings()
    provider_name = (name or settings.SPEAKING_LIVE_CONVERSATION_PROVIDER or "hume_evi").strip().lower()
    if provider_name not in _SUPPORTED:
        raise ProviderLiveUnavailableError(
            f"Unknown live conversation provider: {provider_name}",
            detail=f"supported={sorted(_SUPPORTED)}",
        )
    if provider_name == "hume_evi":
        if not (settings.HUME_API_KEY or "").strip():
            raise ProviderLiveUnavailableError("HUME_API_KEY not configured for hume_evi")
        if not (settings.HUME_EVI_CONFIG_ID or "").strip():
            raise ProviderLiveUnavailableError("HUME_EVI_CONFIG_ID not configured for hume_evi")
    return _SUPPORTED[provider_name]()
