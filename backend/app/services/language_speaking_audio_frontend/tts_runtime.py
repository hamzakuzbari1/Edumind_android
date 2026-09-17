"""Shared TTS helper for Speaking voice turns.

Prefers local Supertonic when LANGUAGE_TTS_PROVIDER=supertonic (configured default).
Falls back to OpenAI speech API when Supertonic is unavailable.
Never owns dialogue reasoning. Failures return None (text mode continues).
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_OPENAI_SPEECH_URL = "https://api.openai.com/v1/audio/speech"

TTS_AUDIO_FORMAT = "mp3"
TTS_AUDIO_MIME = "audio/mpeg"
_MAX_TTS_CHARS = 1000


async def _synthesize_supertonic_line(text: str) -> tuple[bytes, str] | None:
    """Local Supertonic WAV synthesis for English tutor lines."""
    try:
        from app.services.language_supertonic_service import (
            language_tts_audio_mime_type,
            language_tts_enabled,
            synthesize_language_speech,
        )
    except Exception:  # noqa: BLE001
        return None

    if not language_tts_enabled():
        return None

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = Path(tmp.name)
        ok = await synthesize_language_speech(
            text,
            language="en",
            output_path=tmp_path,
        )
        if not ok or not tmp_path.exists():
            return None
        audio = tmp_path.read_bytes()
        if not audio:
            return None
        return audio, language_tts_audio_mime_type()
    except Exception:  # noqa: BLE001 — never load-bearing
        logger.exception("Supertonic speaking TTS failed; trying OpenAI fallback")
        return None
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass


async def _synthesize_openai_line(text: str) -> tuple[bytes, str] | None:
    api_key = (getattr(settings, "OPENAI_API_KEY", None) or "").strip()
    if not api_key:
        return None

    model = (getattr(settings, "SPEAKING_TTS_MODEL", None) or "gpt-4o-mini-tts").strip()
    voice = (getattr(settings, "SPEAKING_TTS_VOICE", None) or "verse").strip()
    timeout_raw = int(getattr(settings, "SPEAKING_TTS_TIMEOUT_SECONDS", 30) or 30)
    timeout_s = max(5, min(120, timeout_raw))

    payload = {
        "model": model,
        "voice": voice,
        "input": text,
        "response_format": TTS_AUDIO_FORMAT,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=float(timeout_s)) as client:
                resp = await client.post(
                    _OPENAI_SPEECH_URL,
                    headers=headers,
                    json=payload,
                )
                if resp.status_code == 429 and attempt == 0:
                    await asyncio.sleep(1.2)
                    continue
                resp.raise_for_status()
                audio = resp.content
            if not audio:
                return None
            return audio, TTS_AUDIO_MIME
        except Exception as exc:  # noqa: BLE001 — TTS is never load-bearing
            last_error = exc
            if attempt == 0:
                continue
            logger.exception(
                "OpenAI speaking TTS failed; turn continues in text mode (%s)",
                last_error,
            )
            return None
    return None


async def synthesize_spoken_line(text: str) -> tuple[bytes, str] | None:
    """Synthesize one short spoken line. None => caller stays in text mode."""
    line = (text or "").strip()
    if not line:
        return None
    line = line[:_MAX_TTS_CHARS]

    local = await _synthesize_supertonic_line(line)
    if local is not None:
        return local

    return await _synthesize_openai_line(line)
