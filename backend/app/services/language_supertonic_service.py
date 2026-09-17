"""Supertonic TTS adapter for the language-learning module."""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import wave
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.services.tts_service import prepare_synthesis_text

logger = logging.getLogger(__name__)
settings = get_settings()


def language_tts_audio_extension() -> str:
    return ".wav"


def language_tts_audio_mime_type() -> str:
    return "audio/wav"


def language_tts_enabled() -> bool:
    return bool(settings.ENABLE_TTS and (settings.LANGUAGE_TTS_PROVIDER or "").strip().lower() == "supertonic")


def _default_language_voice() -> str:
    return (
        settings.LANGUAGE_SUPERTONIC_VOICE_FEMALE
        or settings.LANGUAGE_SUPERTONIC_VOICE
        or "F1"
    ).strip() or "F1"


@lru_cache(maxsize=1)
def _tts_engine():
    from supertonic import TTS

    return TTS(auto_download=bool(settings.LANGUAGE_SUPERTONIC_AUTO_DOWNLOAD))


@lru_cache(maxsize=16)
def _voice_style(voice_name: str):
    return _tts_engine().get_voice_style(voice_name)


_engine_load_task: asyncio.Task | None = None


async def _ensure_engine_loaded() -> None:
    """Lazily load the Supertonic engine exactly once, even under concurrent callers.

    The first real synthesis after a fresh process start can trigger a one-time model download
    that takes minutes. Without this guard, multiple concurrent callers (e.g. several listening
    content-preparation attempts overlapping) would each independently call TTS(auto_download=True),
    racing on the same on-disk download staging directory (observed: "Directory not empty" cleanup
    warnings and outright download failures). asyncio.shield ensures a caller that stops waiting
    (e.g. an outer per-item timeout) never cancels the shared load itself -- it keeps running in
    the background, and the very next caller (or the same one retrying) reuses the same in-flight
    load instead of starting a duplicate.
    """
    global _engine_load_task
    if _tts_engine.cache_info().currsize > 0:
        return
    if _engine_load_task is None:
        _engine_load_task = asyncio.ensure_future(asyncio.to_thread(_tts_engine))
    await asyncio.shield(_engine_load_task)


def _synthesize_sync(text: str, *, language: str, output_path: Path, voice_name: str) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    engine = _tts_engine()
    style = _voice_style(voice_name)
    wav, _duration = engine.synthesize(text, voice_style=style, lang=language)
    engine.save_audio(wav, str(output_path))
    return output_path.exists() and output_path.stat().st_size > 0


def _concat_wavs(paths: list[Path], output_path: Path) -> bool:
    if not paths:
        return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(paths[0]), "rb") as first:
        params = first.getparams()
        first_frames = first.readframes(first.getnframes())
    with wave.open(str(output_path), "wb") as out:
        out.setparams(params)
        out.writeframes(first_frames)
        for path in paths[1:]:
            with wave.open(str(path), "rb") as segment:
                if segment.getparams()[:3] != params[:3]:
                    return False
                out.writeframes(segment.readframes(segment.getnframes()))
    return output_path.exists() and output_path.stat().st_size > 0


def _synthesize_segments_sync(
    segments: list[tuple[str, str]], *, language: str, output_path: Path
) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_paths: list[Path] = []
    try:
        for text, voice_name in segments:
            fd, tmp_name = tempfile.mkstemp(dir=str(output_path.parent), suffix=language_tts_audio_extension())
            os.close(fd)
            tmp_path = Path(tmp_name)
            temp_paths.append(tmp_path)
            if not _synthesize_sync(text, language=language, output_path=tmp_path, voice_name=voice_name):
                return False
        if len(temp_paths) == 1:
            os.replace(temp_paths[0], output_path)
            temp_paths = []
            return output_path.exists() and output_path.stat().st_size > 0
        return _concat_wavs(temp_paths, output_path)
    finally:
        for tmp_path in temp_paths:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass


async def synthesize_language_speech(
    text: str,
    *,
    language: str = "en",
    output_path: Path,
    voice_name: str | None = None,
) -> bool:
    """Generate speech with Supertone/supertonic-3."""

    cleaned = prepare_synthesis_text(text)
    if not cleaned or not language_tts_enabled():
        return False

    voice = (voice_name or _default_language_voice()).strip() or _default_language_voice()
    lang = (language or "en").strip().lower()
    try:
        await _ensure_engine_loaded()
        return await asyncio.to_thread(
            _synthesize_sync,
            cleaned,
            language=lang,
            output_path=output_path,
            voice_name=voice,
        )
    except Exception as exc:
        logger.warning("Supertonic synthesis failed: %s", exc)
        return False


async def synthesize_language_speech_segments(
    segments: list[tuple[str, str]],
    *,
    language: str = "en",
    output_path: Path,
) -> bool:
    """Generate one audio file from ordered (text, voice_name) segments."""

    if not language_tts_enabled():
        return False

    normalized: list[tuple[str, str]] = []
    fallback_voice = _default_language_voice()
    for text, voice_name in segments:
        cleaned = prepare_synthesis_text(text)
        voice = (voice_name or fallback_voice).strip() or fallback_voice
        if cleaned:
            normalized.append((cleaned, voice))
    if not normalized:
        return False

    lang = (language or "en").strip().lower()
    try:
        await _ensure_engine_loaded()
        return await asyncio.to_thread(
            _synthesize_segments_sync,
            normalized,
            language=lang,
            output_path=output_path,
        )
    except Exception as exc:
        logger.warning("Supertonic segment synthesis failed: %s", exc)
        return False
