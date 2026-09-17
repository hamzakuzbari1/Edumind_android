"""WritingModelProvider factory (W6) — sole entry for LLM generation in writing runtime."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import get_settings
from app.services.language_writing_runtime.provider_types import (
    ModelCapabilityFlags,
    WritingModelGenerateRequest,
    WritingModelGenerateResponse,
    WritingModelProviderInfo,
)

settings = get_settings()


class WritingModelProvider(ABC):
    """Provider abstraction — business services call generate() only."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def temperature(self) -> float: ...

    @property
    @abstractmethod
    def max_tokens(self) -> int: ...

    @property
    @abstractmethod
    def capabilities(self) -> ModelCapabilityFlags: ...

    def info(self) -> WritingModelProviderInfo:
        return WritingModelProviderInfo(
            provider_name=self.provider_name,
            model_name=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            capabilities=self.capabilities,
        )

    @abstractmethod
    async def generate(self, request: WritingModelGenerateRequest) -> WritingModelGenerateResponse: ...


def get_writing_model_provider(*, provider: str | None = None) -> WritingModelProvider:
    """Resolve provider by name — claude (default), mock (tests/dev without API key)."""
    name = (provider or settings.WRITING_MODEL_PROVIDER or "claude").strip().lower()
    if name == "mock":
        from app.services.language_writing_runtime.providers.mock_writing_provider import MockWritingModelProvider

        return MockWritingModelProvider()
    if name in ("claude", "anthropic"):
        from app.services.claude_service import is_claude_configured
        from app.services.language_writing_runtime.providers.claude_writing_provider import ClaudeWritingModelProvider

        if not is_claude_configured():
            from app.services.language_writing_runtime.providers.mock_writing_provider import MockWritingModelProvider

            return MockWritingModelProvider()
        return ClaudeWritingModelProvider()
    raise ValueError(f"Unknown writing model provider: {name}")
