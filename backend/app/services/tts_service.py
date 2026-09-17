"""Text-to-speech for AI tutor answers via ElevenLabs."""

from __future__ import annotations

import logging
import re
import time
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.services.elevenlabs_service import ElevenLabsError, synthesize_speech

logger = logging.getLogger(__name__)
settings = get_settings()


def _allowed_languages() -> set[str]:
    return {
        lang.strip().lower()
        for lang in (settings.TTS_ALLOWED_LANGUAGES or "ar,en,fr").split(",")
        if lang.strip()
    }


def _tts_language() -> str:
    language = (settings.TTS_LANGUAGE or "ar").strip().lower()
    allowed = _allowed_languages()
    if language in allowed:
        return language
    fallback = "ar" if "ar" in allowed else next(iter(allowed), "ar")
    logger.warning("Unsupported TTS_LANGUAGE=%s; falling back to %s", language, fallback)
    return fallback


def _resolve_language(language: str | None) -> str:
    if language:
        normalized = language.strip().lower()
        allowed = _allowed_languages()
        if normalized in allowed:
            return normalized
        logger.warning("Unsupported TTS language=%s; falling back to default", language)
    return _tts_language()


def tts_audio_extension() -> str:
    output_format = (settings.ELEVENLABS_OUTPUT_FORMAT or "").strip().lower()
    if output_format.startswith("wav"):
        return ".wav"
    if output_format.startswith("pcm"):
        return ".pcm"
    if output_format.startswith("ulaw"):
        return ".ulaw"
    if output_format.startswith("alaw"):
        return ".alaw"
    if output_format.startswith("opus"):
        return ".opus"
    return ".mp3"


def tts_audio_mime_type() -> str:
    ext = tts_audio_extension()
    if ext == ".wav":
        return "audio/wav"
    if ext == ".opus":
        return "audio/opus"
    if ext in (".pcm", ".ulaw", ".alaw"):
        return "application/octet-stream"
    return "audio/mpeg"


async def synthesize_cloned_speech(
    text: str,
    speaker_wav: str | None = None,
    *,
    language: str,
    output_path: Path,
    voice_id: str | None = None,
) -> bool:
    """Generate cloned speech at output_path with ElevenLabs."""

    cleaned = prepare_synthesis_text(text)
    if not settings.ENABLE_TTS or not cleaned:
        return False
    if (settings.TTS_PROVIDER or "elevenlabs").strip().lower() != "elevenlabs":
        logger.info("ElevenLabs synthesis skipped: TTS_PROVIDER=%s", settings.TTS_PROVIDER)
        return False

    resolved_voice_id = (voice_id or "").strip()
    if not resolved_voice_id:
        logger.warning("ElevenLabs synthesis skipped: missing voice_id")
        return False

    try:
        return await synthesize_speech(
            text=cleaned,
            voice_id=resolved_voice_id,
            output_path=output_path,
            language=_resolve_language(language),
        )
    except ElevenLabsError as exc:
        logger.warning("ElevenLabs synthesis failed: %s", exc)
        return False


async def synthesize_answer_audio(
    text: str,
    speaker_wav: str | None,
    lesson_id: int,
    *,
    voice_id: str | None = None,
) -> str | None:
    """Return a public /uploads URL for generated audio, or None on fallback."""

    text = prepare_synthesis_text(text)
    if not settings.ENABLE_TTS or not text:
        return None

    if not (voice_id or "").strip():
        logger.warning("Answer TTS skipped: missing ElevenLabs voice_id lesson_id=%s", lesson_id)
        return None

    started = time.perf_counter()
    try:
        output_dir = Path(settings.TTS_OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"lesson_{lesson_id}_{uuid.uuid4().hex}{tts_audio_extension()}"
        ok = await synthesize_cloned_speech(
            text,
            speaker_wav,
            language=_tts_language(),
            output_path=output_path,
            voice_id=voice_id,
        )
        duration_s = time.perf_counter() - started
        if not ok:
            logger.warning("Answer TTS synthesis failed lesson_id=%s duration_s=%.2f", lesson_id, duration_s)
            return None
        url = _upload_url(output_path)
        logger.info("Answer TTS synthesis ok lesson_id=%s duration_s=%.2f url=%s", lesson_id, duration_s, url)
        return url
    except Exception as exc:
        duration_s = time.perf_counter() - started
        logger.warning("Answer TTS synthesis failed lesson_id=%s duration_s=%.2f error=%s", lesson_id, duration_s, exc)
        return None


def prepare_synthesis_text(text: str, *, max_chars: int | None = None) -> str:
    """Normalize tutor reply text before speech synthesis."""

    cleaned = text or ""
    cleaned = re.sub(r"\[\[EDUSPARK_(?:SOURCES|AUDIO):.*?\]\]", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"(?m)^[ \t]*[-*]\s+", "", cleaned)
    cleaned = re.sub(r"(?m)^[ \t]*\d+[\.)]\s*", "", cleaned)
    cleaned = re.sub(r"[*_`#~>|]+", " ", cleaned)
    cleaned = re.sub(r"[\[\]{}]", " ", cleaned)
    cleaned = re.sub(r"[()]", " ", cleaned)
    cleaned = re.sub(r"\s+([:?!.,])", r"\1", cleaned)
    cleaned = re.sub(r"([?!]){2,}", r"\1", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    limit = max_chars or int(getattr(settings, "TTS_MAX_TEXT_CHARS", 1200) or 1200)
    cleaned = _truncate_for_speech(cleaned, limit)
    return cleaned.strip()


def _truncate_for_speech(text: str, limit: int) -> str:
    """Keep TTS text under limit without ending in the middle of a sentence."""

    if limit <= 0 or len(text) <= limit:
        return text

    candidate = text[:limit].strip()
    min_cut = max(80, int(limit * 0.45))
    sentence_cut = max(candidate.rfind(mark) for mark in (".", "!", "?"))
    if sentence_cut >= min_cut:
        return candidate[: sentence_cut + 1].strip()

    phrase_cut = max(candidate.rfind(mark) for mark in (",", ":"))
    if phrase_cut >= min_cut:
        return candidate[: phrase_cut + 1].strip()

    word_cut = candidate.rfind(" ")
    if word_cut >= min_cut:
        return candidate[:word_cut].strip()
    return candidate


async def synthesize_preview_audio(
    text: str,
    speaker_wav: str | None,
    *,
    sample_id: int,
    voice_id: str | None = None,
) -> str | None:
    """Generate a teacher voice preview clip."""

    if not settings.ENABLE_TTS or not text.strip():
        return None
    if not (voice_id or "").strip():
        logger.warning("Voice preview skipped: missing ElevenLabs voice_id sample_id=%s", sample_id)
        return None

    try:
        output_dir = Path(settings.TTS_OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"voice_preview_{sample_id}_{uuid.uuid4().hex}{tts_audio_extension()}"
        ok = await synthesize_cloned_speech(
            text,
            speaker_wav,
            language=_tts_language(),
            output_path=output_path,
            voice_id=voice_id,
        )
        if not ok:
            return None
        return _upload_url(output_path)
    except Exception as exc:
        logger.warning("Voice preview synthesis failed: %s", exc)
        return None


def _upload_url(path: Path) -> str:
    upload_root = Path(settings.UPLOAD_DIR).resolve()
    rel = path.resolve().relative_to(upload_root).as_posix()
    return f"/uploads/{rel}"
