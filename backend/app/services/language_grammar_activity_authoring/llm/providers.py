"""LLM Authoring Providers (V1.4) — Claude adapter + future-provider stubs."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from app.services.language_grammar_activity_authoring.llm.errors import (
    LLMProviderError,
    LLMTimeoutError,
    LLMTransientError,
)
from app.services.language_grammar_activity_authoring.llm.types import PromptBundle

logger = logging.getLogger(__name__)

JsonGenerator = Callable[[str, str, float], str]


class ClaudeAuthoringProvider:
    """Claude adapter — content author only. Prompts come from Prompt Builder."""

    provider_id = "claude"
    provider_version = "1.0.0"

    def __init__(self, *, json_generator: JsonGenerator | None = None) -> None:
        self._json_generator = json_generator

    def generate_json(
        self,
        prompts: PromptBundle,
        *,
        timeout_seconds: float,
    ) -> str:
        system = f"{prompts.system_prompt}\n\n{prompts.developer_prompt}".strip()
        generator = self._json_generator or _default_claude_json_generator
        try:
            text = generator(prompts.user_prompt, system, timeout_seconds)
        except TimeoutError as exc:
            raise LLMTimeoutError("timeout", str(exc) or "Claude authoring timed out") from exc
        except LLMTimeoutError:
            raise
        except LLMProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMTransientError("transient_failure", f"Claude authoring failed: {exc}") from exc

        if not (text or "").strip():
            raise LLMTransientError("empty_response", "Claude returned empty JSON")
        return text


class GeminiAuthoringProvider:
    """Future Gemini adapter stub — registry-ready, not implemented in V1.4."""

    provider_id = "gemini"
    provider_version = "0.0.0"

    def generate_json(self, prompts: PromptBundle, *, timeout_seconds: float) -> str:
        raise LLMProviderError("not_implemented", "GeminiAuthoringProvider not implemented in V1.4")


class GPTAuthoringProvider:
    """Future GPT adapter stub — registry-ready, not implemented in V1.4."""

    provider_id = "gpt"
    provider_version = "0.0.0"

    def generate_json(self, prompts: PromptBundle, *, timeout_seconds: float) -> str:
        raise LLMProviderError("not_implemented", "GPTAuthoringProvider not implemented in V1.4")


class LocalModelAuthoringProvider:
    """Future local-model adapter stub — registry-ready, not implemented in V1.4."""

    provider_id = "local"
    provider_version = "0.0.0"

    def generate_json(self, prompts: PromptBundle, *, timeout_seconds: float) -> str:
        raise LLMProviderError("not_implemented", "LocalModelAuthoringProvider not implemented in V1.4")


def _default_claude_json_generator(user_prompt: str, system: str, timeout_seconds: float) -> str:
    from app.services.claude_service import generate_claude_json_sync, is_claude_configured

    if not is_claude_configured():
        raise LLMProviderError("claude_not_configured", "ANTHROPIC_API_KEY is not configured")
    try:
        return generate_claude_json_sync(
            user_prompt,
            system=system,
            temperature=0.3,
            max_output_tokens=3500,
            timeout=timeout_seconds,
        )
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "timeout" in msg or "timed out" in msg:
            raise LLMTimeoutError("timeout", str(exc)) from exc
        raise


def builtin_llm_authoring_providers() -> tuple[Any, ...]:
    return (
        ClaudeAuthoringProvider(),
        GeminiAuthoringProvider(),
        GPTAuthoringProvider(),
        LocalModelAuthoringProvider(),
    )
