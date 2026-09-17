"""OpenAI GPT-4o SpeechTranscriptionProvider (S4 production implementation).

Wraps the OpenAI Audio Transcriptions endpoint
(``POST https://api.openai.com/v1/audio/transcriptions``) behind the frozen
``SpeechTranscriptionProvider`` contract. This is the production/default Speaking
transcription provider.

Timing honesty:
- ``gpt-4o-transcribe`` / ``gpt-4o-mini-transcribe`` support only ``json`` /
  ``text`` response formats and DO NOT return word or segment timestamps. When
  such a model is used, timings are reported as unavailable (never fabricated).
- ``whisper-1`` supports ``verbose_json`` with ``timestamp_granularities`` and
  therefore returns real segment/word timings, which are surfaced when present.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.services.language_speaking_providers.capabilities import TranscriptionCapabilities
from app.services.language_speaking_providers.providers import SpeechTranscriptionProvider

logger = logging.getLogger(__name__)
settings = get_settings()

_OPENAI_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"

# Models known to return real word/segment timestamps via verbose_json.
_TIMESTAMP_CAPABLE_MODELS = frozenset({"whisper-1"})


def _resolve_model() -> str:
    override = (settings.SPEAKING_OPENAI_STT_MODEL or "").strip()
    if override:
        return override
    return (settings.LANGUAGE_STT_MODEL or "gpt-4o-transcribe").strip()


def _api_key() -> str:
    return (settings.OPENAI_API_KEY or "").strip()


def _model_supports_timestamps(model: str) -> bool:
    return model.strip().lower() in _TIMESTAMP_CAPABLE_MODELS


def _map_verbose_segments(payload: dict) -> tuple[list[dict], list[dict], float | None]:
    """Extract real segment/word timings from a verbose_json payload."""
    segments: list[dict] = []
    words: list[dict] = []
    logprobs: list[float] = []

    for seg in payload.get("segments") or []:
        avg_logprob = seg.get("avg_logprob")
        if avg_logprob is not None:
            logprobs.append(float(avg_logprob))
        segments.append(
            {
                "text": str(seg.get("text") or "").strip(),
                "start_sec": float(seg.get("start") or 0.0),
                "end_sec": float(seg.get("end") or 0.0),
                "confidence": float(avg_logprob) if avg_logprob is not None else 0.0,
            }
        )

    for word in payload.get("words") or []:
        words.append(
            {
                "word": str(word.get("word") or "").strip(),
                "start_sec": float(word.get("start") or 0.0),
                "end_sec": float(word.get("end") or 0.0),
                "confidence": 0.0,
            }
        )

    avg_logprob = sum(logprobs) / len(logprobs) if logprobs else None
    return segments, words, avg_logprob


def _post_openai(
    audio_path: Path,
    *,
    model: str,
    api_key: str,
    language: str,
    initial_prompt: str,
    timeout_s: int,
) -> dict[str, object]:
    """Synchronous OpenAI transcription HTTP call (runs in a worker thread)."""
    data: dict[str, object] = {"model": model, "language": language}
    if initial_prompt:
        data["prompt"] = initial_prompt

    if _model_supports_timestamps(model):
        data["response_format"] = "verbose_json"
        data["timestamp_granularities[]"] = ["segment", "word"]
    else:
        data["response_format"] = "json"

    with audio_path.open("rb") as audio_file:
        response = httpx.post(
            _OPENAI_TRANSCRIPTIONS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (audio_path.name, audio_file, "audio/wav")},
            data=data,
            timeout=httpx.Timeout(float(timeout_s)),
        )

    if response.status_code >= 400:
        raise RuntimeError(
            f"OpenAI transcription failed: status={response.status_code} "
            f"detail={response.text[:500]}"
        )

    try:
        payload = response.json()
    except ValueError as exc:  # pragma: no cover - defensive
        raise RuntimeError("OpenAI transcription returned invalid JSON") from exc

    text = str(payload.get("text") or "").strip()
    result: dict[str, object] = {
        "text": text,
        "language": str(payload.get("language") or language),
        "segments": [],
        "words": [],
        "model": model,
        "provider_name": "openai",
        "provider_version": "openai-audio-v1",
        "processing_version": "s4_openai",
        "response_format": str(data["response_format"]),
    }

    if _model_supports_timestamps(model) and isinstance(payload, dict):
        segments, words, avg_logprob = _map_verbose_segments(payload)
        result["segments"] = segments
        result["words"] = words
        if avg_logprob is not None:
            # verbose_json avg_logprob (<=0). Map heuristically into [0, 1].
            result["provider_confidence"] = max(0.0, min(1.0, 1.0 + avg_logprob))
    # For gpt-4o json responses there is no confidence field: intentionally omit
    # "provider_confidence" so downstream never treats unknown as low quality.

    duration = payload.get("duration")
    if duration is not None:
        result["duration_s"] = float(duration)
    return result


class GPT4oTranscriptionProvider(SpeechTranscriptionProvider):
    """Production transcription via OpenAI GPT-4o Audio Transcriptions API."""

    def capabilities(self) -> TranscriptionCapabilities:
        model = _resolve_model()
        return TranscriptionCapabilities(
            supports_word_timestamps=_model_supports_timestamps(model),
            supports_confidence_scores=_model_supports_timestamps(model),
            supports_streaming=False,
            supported_languages=("en",),
            provider_name="openai",
        )

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
        language: str = "en",
        initial_prompt: str = "",
    ) -> dict[str, object]:
        model = _resolve_model()
        if not audio_bytes:
            return {
                "text": "",
                "language": language,
                "segments": [],
                "words": [],
                "model": model,
                "provider_name": "openai",
            }

        api_key = _api_key()
        if not api_key:
            # No silent fallback: a configured OpenAI provider without a key fails.
            raise RuntimeError("OPENAI_API_KEY is not configured for GPT-4o transcription")

        timeout = max(1, int(settings.SPEAKING_TRANSCRIPTION_TIMEOUT_SECONDS or 120))
        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_bytes)
                tmp_path = Path(tmp.name)
            return await asyncio.wait_for(
                asyncio.to_thread(
                    _post_openai,
                    tmp_path,
                    model=model,
                    api_key=api_key,
                    language=language,
                    initial_prompt=initial_prompt,
                    timeout_s=timeout,
                ),
                timeout=timeout + 15,
            )
        except asyncio.TimeoutError as exc:
            raise TimeoutError("OpenAI transcription timed out") from exc
        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
