"""LLM Authoring Provider Registry (V1.4) — swap providers without architecture changes."""

from __future__ import annotations

from app.services.language_grammar_activity_authoring.llm.errors import LLMProviderError
from app.services.language_grammar_activity_authoring.llm.providers import (
    builtin_llm_authoring_providers,
)
from app.services.language_grammar_activity_authoring.llm.types import LLMAuthoringProvider


class LLMAuthoringProviderRegistry:
    """Deterministic registry of LLM authoring providers."""

    def __init__(self, providers: tuple[LLMAuthoringProvider, ...] | None = None) -> None:
        loaded = builtin_llm_authoring_providers() if providers is None else providers
        by_id: dict[str, LLMAuthoringProvider] = {}
        for provider in loaded:
            pid = getattr(provider, "provider_id", "") or ""
            if not str(pid).strip():
                raise LLMProviderError("missing_provider_id", "Provider missing provider_id")
            if pid in by_id:
                raise LLMProviderError("duplicate_provider_id", f"Duplicate provider id: {pid}")
            by_id[pid] = provider
        self._by_id = by_id

    def get(self, provider_id: str) -> LLMAuthoringProvider:
        provider = self._by_id.get(provider_id)
        if provider is None:
            raise LLMProviderError("unknown_provider", f"Unknown LLM authoring provider: {provider_id}")
        return provider

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_id.keys()))

    def register(self, provider: LLMAuthoringProvider) -> None:
        pid = provider.provider_id
        if pid in self._by_id:
            raise LLMProviderError("duplicate_provider_id", f"Duplicate provider id: {pid}")
        self._by_id[pid] = provider


_DEFAULT_REGISTRY: LLMAuthoringProviderRegistry | None = None


def get_default_llm_authoring_registry() -> LLMAuthoringProviderRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = LLMAuthoringProviderRegistry()
    return _DEFAULT_REGISTRY


def reset_default_llm_authoring_registry_for_tests() -> None:
    global _DEFAULT_REGISTRY
    _DEFAULT_REGISTRY = None
