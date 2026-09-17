"""Listening lesson audio renderer — gender-aware Supertonic synthesis."""

from __future__ import annotations

import logging
from pathlib import Path

from app.services.language_listening_tts.speakers import build_synthesis_segments
from app.services.language_supertonic_service import (
    language_tts_audio_extension,
    synthesize_language_speech_segments,
)

logger = logging.getLogger(__name__)


def _safe_voice_name(value: str) -> str:
    cleaned = "".join(ch if (ch.isalnum() or ch in "-_.") else "-" for ch in str(value or "").strip())
    return cleaned.strip("-.") or "unknown"


def listening_cache_filename(segments: list[tuple[str, str]]) -> str:
    voices = sorted({_safe_voice_name(voice) for _, voice in segments if voice})
    if len(voices) == 1:
        return f"supertonic_{voices[0]}{language_tts_audio_extension()}"
    if voices:
        return f"supertonic_multivoice_{'_'.join(voices)}{language_tts_audio_extension()}"
    return f"supertonic_unknown{language_tts_audio_extension()}"


async def synthesize_listening_lesson_audio(
    body: dict | None,
    *,
    output_path: Path,
    language: str = "en",
) -> bool:
    segments = build_synthesis_segments(body)
    if not segments:
        return False
    ok = await synthesize_language_speech_segments(
        segments,
        language=language,
        output_path=output_path,
    )
    if ok:
        logger.info(
            "Listening multivoice synthesis segments=%s voices=%s",
            len(segments),
            sorted({v for _, v in segments}),
        )
    return ok
