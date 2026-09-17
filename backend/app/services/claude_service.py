"""Claude Sonnet LLM service — centralized Anthropic integration for all text/JSON LLM calls."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

T = TypeVar("T", bound=BaseModel)


@dataclass(slots=True)
class ClaudeCallResult:
    """Text plus Anthropic response metadata."""

    text: str
    model: str | None = None
    stop_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None

    def to_metadata_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "stop_reason": self.stop_reason,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


_JSON_ONLY_SUFFIX = (
    "\n\nRespond with valid JSON only. Do not wrap the JSON in markdown fences or add commentary."
)

_client: Any | None = None


def is_claude_configured() -> bool:
    return bool((settings.ANTHROPIC_API_KEY or "").strip())


def claude_model_name(model_name: str | None = None) -> str:
    return (model_name or settings.CLAUDE_MODEL or "claude-sonnet-5").strip()


def _model_supports_temperature(model: str) -> bool:
    """Newer Claude models (4.6 generation and later, e.g. claude-sonnet-5) deprecate
    the `temperature` sampling parameter and reject requests that include it. Only send
    `temperature` for older dated snapshots (e.g. claude-sonnet-4-5-20250929)."""
    m = (model or "").lower()
    legacy_prefixes = (
        "claude-3",
        "claude-sonnet-4-0",
        "claude-sonnet-4-5",
        "claude-opus-4-0",
        "claude-opus-4-1",
        "claude-haiku-4-5",
    )
    return m.startswith(legacy_prefixes)


def _get_client():
    global _client
    if _client is None:
        if not is_claude_configured():
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        from anthropic import Anthropic

        _client = Anthropic(api_key=settings.ANTHROPIC_API_KEY.strip())
    return _client


def _extract_text(response: Any) -> str:
    parts: list[str] = []
    for block in getattr(response, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts).strip()


def _result_from_response(response: Any, *, fallback_model: str | None = None) -> ClaudeCallResult:
    usage = getattr(response, "usage", None)
    return ClaudeCallResult(
        text=_extract_text(response),
        model=getattr(response, "model", None) or fallback_model,
        stop_reason=getattr(response, "stop_reason", None),
        input_tokens=getattr(usage, "input_tokens", None) if usage is not None else None,
        output_tokens=getattr(usage, "output_tokens", None) if usage is not None else None,
    )


def _messages_create_sync(
    *,
    prompt: str,
    system: str = "",
    temperature: float = 0.2,
    max_tokens: int = 1024,
    model_name: str | None = None,
    timeout: float = 120.0,
    return_response: bool = False,
) -> str | Any:
    client = _get_client()
    kwargs: dict[str, Any] = {
        "model": claude_model_name(model_name),
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "timeout": timeout,
    }
    # Claude Sonnet 5 (and other 4.6-generation+ models) reject `temperature`
    # (`invalid_request_error: temperature is deprecated for this model`).
    if temperature is not None and _model_supports_temperature(claude_model_name(model_name)):
        kwargs["temperature"] = temperature
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    if return_response:
        return response
    return _extract_text(response)


def generate_claude_text_sync(
    prompt: str,
    *,
    system: str = "",
    temperature: float = 0.2,
    max_tokens: int = 1024,
    model_name: str | None = None,
    timeout: float = 120.0,
) -> str:
    result = _messages_create_sync(
        prompt=prompt,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
        model_name=model_name,
        timeout=timeout,
    )
    return str(result)


def generate_claude_json_sync(
    prompt: str,
    *,
    system: str = "",
    temperature: float = 0.4,
    max_output_tokens: int = 1024,
    model_name: str | None = None,
    timeout: float = 120.0,
) -> str:
    json_system = f"{system}{_JSON_ONLY_SUFFIX}" if system else _JSON_ONLY_SUFFIX.strip()
    return generate_claude_text_sync(
        prompt,
        system=json_system,
        temperature=temperature,
        max_tokens=max_output_tokens,
        model_name=model_name,
        timeout=timeout,
    )


def generate_claude_json_result_sync(
    prompt: str,
    *,
    system: str = "",
    temperature: float = 0.4,
    max_output_tokens: int = 1024,
    model_name: str | None = None,
    timeout: float = 120.0,
) -> ClaudeCallResult:
    """Structured JSON via Claude with provider metadata."""

    resolved_model = claude_model_name(model_name)
    if not is_claude_configured():
        return ClaudeCallResult(text="", model=resolved_model)
    json_system = f"{system}{_JSON_ONLY_SUFFIX}" if system else _JSON_ONLY_SUFFIX.strip()
    response = _messages_create_sync(
        prompt=prompt,
        system=json_system,
        temperature=temperature,
        max_tokens=max_output_tokens,
        model_name=resolved_model,
        timeout=timeout,
        return_response=True,
    )
    return _result_from_response(response, fallback_model=resolved_model)


async def generate_claude_text(
    prompt: str,
    *,
    system: str = "",
    temperature: float = 0.2,
    max_tokens: int = 1024,
    model_name: str | None = None,
    timeout: float = 120.0,
) -> str:
    if not is_claude_configured():
        return ""
    try:
        return await asyncio.to_thread(
            _messages_create_sync,
            prompt=prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            model_name=model_name,
            timeout=timeout,
        )
    except Exception as exc:
        logger.warning("Claude text generation failed: %s", exc)
        return ""


async def generate_claude_json_result(
    prompt: str,
    *,
    system: str = "",
    temperature: float = 0.4,
    max_output_tokens: int = 1024,
    model_name: str | None = None,
    timeout: float = 120.0,
) -> ClaudeCallResult:
    """Structured JSON via Claude, preserving Anthropic response metadata."""

    resolved_model = claude_model_name(model_name)
    if not is_claude_configured():
        return ClaudeCallResult(text="", model=resolved_model)
    json_system = f"{system}{_JSON_ONLY_SUFFIX}" if system else _JSON_ONLY_SUFFIX.strip()
    try:
        response = await asyncio.to_thread(
            _messages_create_sync,
            prompt=prompt,
            system=json_system,
            temperature=temperature,
            max_tokens=max_output_tokens,
            model_name=resolved_model,
            timeout=timeout,
            return_response=True,
        )
        return _result_from_response(response, fallback_model=resolved_model)
    except Exception as exc:
        logger.warning("Claude JSON generation failed: %s", exc)
        return ClaudeCallResult(text="", model=resolved_model)


async def generate_claude_json(
    prompt: str,
    *,
    system: str = "",
    temperature: float = 0.4,
    max_output_tokens: int = 1024,
    model_name: str | None = None,
    timeout: float = 120.0,
) -> str:
    """Structured JSON via Claude — shared helper for modules that need JSON output."""
    if not is_claude_configured():
        return ""
    json_system = f"{system}{_JSON_ONLY_SUFFIX}" if system else _JSON_ONLY_SUFFIX.strip()
    return await generate_claude_text(
        prompt,
        system=json_system,
        temperature=temperature,
        max_tokens=max_output_tokens,
        model_name=model_name,
        timeout=timeout,
    )


async def generate_claude_json_model(
    prompt: str,
    *,
    system: str,
    model_type: type[T],
    temperature: float = 0.3,
    max_output_tokens: int = 2048,
    model_name: str | None = None,
) -> T | None:
    """Generate JSON and validate against a Pydantic model."""
    raw = await generate_claude_json(
        prompt,
        system=system,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        model_name=model_name,
    )
    if not raw:
        return None
    try:
        return model_type.model_validate_json(raw)
    except Exception:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return model_type.model_validate_json(raw[start:end])
            except Exception as exc:
                logger.warning("Claude structured JSON validation failed: %s", exc)
        return None


async def assess_audio_with_claude_json(
    *,
    audio_bytes: bytes,
    mime: str,
    system: str,
    prompt: str,
    model_type: type[T],
    temperature: float = 0.3,
    max_output_tokens: int = 2048,
    model_name: str | None = None,
) -> T | None:
    """Audio LLM scoring via transcript + Claude (Claude has no native audio input).

    Uses the existing Language STT provider (OpenAI GPT-4o Transcribe) to transcribe
    the audio, then evaluates with the same rubric prompts via Claude.
    """
    if not audio_bytes or not is_claude_configured():
        return None

    from app.services.language_transcription_service import transcribe_english_audio

    suffix = ".webm"
    if mime:
        mime_base = mime.split(";")[0].strip().lower()
        suffix_map = {
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
            "audio/mpeg": ".mp3",
            "audio/mp3": ".mp3",
            "audio/ogg": ".ogg",
            "audio/mp4": ".m4a",
            "audio/x-m4a": ".m4a",
            "audio/aac": ".aac",
            "audio/flac": ".flac",
        }
        suffix = suffix_map.get(mime_base, ".webm")

    try:
        stt = await transcribe_english_audio(audio_bytes, suffix=suffix)
        transcript = (stt.text or "").strip()
    except Exception as exc:
        logger.warning("Audio transcription for Claude assessment failed: %s", exc)
        return None

    if not transcript:
        return None

    enriched_prompt = (
        f"{prompt}\n\n"
        f"Transcription of the learner audio (via speech-to-text):\n\"\"\"\n{transcript}\n\"\"\"\n"
        "Evaluate delivery (fluency, hesitation, clarity) from disfluencies and wording in the transcript."
    )
    return await generate_claude_json_model(
        enriched_prompt,
        system=system,
        model_type=model_type,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        model_name=model_name,
    )
