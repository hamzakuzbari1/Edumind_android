"""Claude WritingModelProvider (W6) — only module that calls Claude for writing generation."""

from __future__ import annotations

import logging
import time

from app.core.config import get_settings
from app.services.claude_service import claude_model_name, generate_claude_json, is_claude_configured
from app.services.language_writing_runtime.claude_prompt_adapter import prompt_bundle_to_claude_messages
from app.services.language_writing_runtime.errors import WritingRuntimeError, WritingRuntimeErrorCode, WritingRuntimeException
from app.services.language_writing_runtime.model_provider import WritingModelProvider
from app.services.language_writing_runtime.provider_types import (
    ModelCapabilityFlags,
    WritingModelGenerateRequest,
    WritingModelGenerateResponse,
)

logger = logging.getLogger(__name__)
settings = get_settings()


def _map_provider_exception(exc: Exception, *, provider_name: str, model_name: str) -> WritingRuntimeError:
    message = str(exc).lower()
    if "timeout" in message or "timed out" in message:
        return WritingRuntimeError(
            code=WritingRuntimeErrorCode.provider_timeout,
            message="Claude request timed out",
            retryable=True,
            provider_name=provider_name,
            model_name=model_name,
        )
    if "rate" in message and "limit" in message:
        return WritingRuntimeError(
            code=WritingRuntimeErrorCode.provider_rate_limit,
            message="Claude rate limit exceeded",
            retryable=True,
            provider_name=provider_name,
            model_name=model_name,
        )
    return WritingRuntimeError(
        code=WritingRuntimeErrorCode.provider_error,
        message=f"Claude generation failed: {exc}",
        retryable=False,
        provider_name=provider_name,
        model_name=model_name,
    )


class ClaudeWritingModelProvider(WritingModelProvider):
    """Claude integration — input: WritingPromptBundle; output: raw JSON text."""

    def __init__(
        self,
        *,
        model_name: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> None:
        self._model_name = claude_model_name(model_name or settings.CLAUDE_MODEL)
        self._temperature = float(temperature if temperature is not None else settings.WRITING_GENERATION_TEMPERATURE)
        self._max_tokens = int(max_tokens if max_tokens is not None else settings.WRITING_GENERATION_MAX_TOKENS)
        self._timeout = float(timeout if timeout is not None else settings.WRITING_GENERATION_TIMEOUT_SECONDS)

    @property
    def provider_name(self) -> str:
        return "claude"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def temperature(self) -> float:
        return self._temperature

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @property
    def capabilities(self) -> ModelCapabilityFlags:
        return ModelCapabilityFlags(
            supports_json_mode=True,
            supports_streaming=False,
            supports_vision=False,
            supports_local_inference=False,
            provider_family="claude",
        )

    async def generate(self, request: WritingModelGenerateRequest) -> WritingModelGenerateResponse:
        if not is_claude_configured():
            raise WritingRuntimeException(
                WritingRuntimeError(
                    code=WritingRuntimeErrorCode.provider_unavailable,
                    message="ANTHROPIC_API_KEY is not configured",
                    retryable=False,
                    provider_name=self.provider_name,
                    model_name=self.model_name,
                )
            )

        system, user = prompt_bundle_to_claude_messages(request.prompt_bundle)
        started = time.perf_counter()
        try:
            raw_text = await generate_claude_json(
                user,
                system=system,
                temperature=self._temperature,
                max_output_tokens=self._max_tokens,
                model_name=self._model_name,
                timeout=self._timeout,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Claude writing generation failed: %s", exc)
            raise WritingRuntimeException(_map_provider_exception(exc, provider_name=self.provider_name, model_name=self.model_name)) from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        if not raw_text.strip():
            raise WritingRuntimeException(
                WritingRuntimeError(
                    code=WritingRuntimeErrorCode.provider_error,
                    message="Claude returned empty response",
                    retryable=True,
                    provider_name=self.provider_name,
                    model_name=self.model_name,
                )
            )

        llm_version = f"{self.provider_name}:{self.model_name}"
        return WritingModelGenerateResponse(
            raw_text=raw_text,
            provider_name=self.provider_name,
            model_name=self.model_name,
            llm_version=llm_version,
            duration_ms=duration_ms,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
