"""Activity Provider Registry (G3.3) — swap providers without Runtime changes."""

from __future__ import annotations

from app.services.language_grammar_activity_provider.providers import (
    CachedProvider,
    ClaudeProvider,
    FutureLLMProvider,
    TemplateProvider,
)
from app.services.language_grammar_activity_provider.types import (
    GrammarActivityProvider,
    GrammarActivityProviderId,
)


class GrammarActivityProviderRegistry:
    """Deterministic registry of GrammarActivityProvider implementations."""

    def __init__(self, providers: tuple[GrammarActivityProvider, ...] | None = None) -> None:
        self._providers: tuple[GrammarActivityProvider, ...] = providers or default_providers()
        by_id: dict[GrammarActivityProviderId, GrammarActivityProvider] = {}
        for provider in self._providers:
            pid = provider.provider_id
            if pid in by_id:
                raise ValueError(f"Duplicate activity provider id: {pid}")
            by_id[pid] = provider
        self._by_id = by_id

    def get(self, provider_id: GrammarActivityProviderId) -> GrammarActivityProvider:
        provider = self._by_id.get(provider_id)
        if provider is None:
            raise KeyError(f"Unknown activity provider: {provider_id}")
        return provider

    def ids(self) -> tuple[GrammarActivityProviderId, ...]:
        return tuple(sorted(self._by_id.keys(), key=lambda x: x.value))

    def all_providers(self) -> tuple[GrammarActivityProvider, ...]:
        return tuple(self._by_id[i] for i in self.ids())


def default_providers() -> tuple[GrammarActivityProvider, ...]:
    return (
        TemplateProvider(),
        CachedProvider(),
        ClaudeProvider(),
        FutureLLMProvider(),
    )


_DEFAULT_REGISTRY = GrammarActivityProviderRegistry()


def get_default_provider_registry() -> GrammarActivityProviderRegistry:
    return _DEFAULT_REGISTRY
