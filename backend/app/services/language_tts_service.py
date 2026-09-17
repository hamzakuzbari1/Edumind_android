"""Lesson audio synthesis for language learning.

Supertonic is preferred when available; OpenAI speech is a non-blocking fallback.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageSkill
from app.models.language.tts_cache import LanguageLessonAudioCache
from app.services.language_listening_tts import (
    build_synthesis_segments,
    listening_cache_filename,
    synthesize_listening_lesson_audio,
)
from app.services.language_supertonic_service import (
    language_tts_audio_extension,
    synthesize_language_speech,
    synthesize_language_speech_segments,
)

logger = logging.getLogger(__name__)
settings = get_settings()

_OPENAI_SPEECH_URL = "https://api.openai.com/v1/audio/speech"
_OPENAI_AUDIO_FORMAT = "mp3"


def _lesson_text(item: LanguageContentItem) -> str:
    body = item.body_json or {}
    text = (
        body.get("audio_transcript")
        or body.get("prompt")
        or body.get("text")
        or body.get("passage")  # reading passages — enables read-along narration
        or item.title
        or ""
    )
    return str(text).strip()


def _audio_dir(content_item_id: int) -> Path:
    d = Path(settings.UPLOAD_DIR) / "language_audio" / str(content_item_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _storage_key(dest: Path) -> str:
    rel = dest.resolve().relative_to(Path(settings.UPLOAD_DIR).resolve())
    return "/".join(rel.parts)


async def synthesize_exam_audio(text: str, *, voice: str = "en-US-AriaNeural") -> str | None:
    """Generate public audio for AI exam listening prompts.

    Uses Supertonic first, then OpenAI speech if Supertonic is unavailable.
    The voice argument is accepted for compatibility with the Fayz exam service.
    """

    cleaned = str(text or "").strip()
    if not cleaned:
        return None

    out_dir = Path(settings.UPLOAD_DIR) / "language_exam_audio"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not settings.ENABLE_TTS:
        return None

    dest = out_dir / f"exam_{uuid.uuid4().hex}{language_tts_audio_extension()}"
    ok = await synthesize_language_speech(
        cleaned,
        language="en",
        output_path=dest,
        voice_name=voice,
    )
    if ok:
        return "/uploads/" + _storage_key(dest)
    fallback = await _synthesize_openai_bytes(cleaned, voice=voice)
    if fallback is None:
        return None
    audio, ext = fallback
    dest = out_dir / f"exam_{uuid.uuid4().hex}.{ext}"
    dest.write_bytes(audio)
    return "/uploads/" + _storage_key(dest)


async def synthesize_exam_audio_segments(segments: list[tuple[str, str]]) -> str | None:
    """Generate one public placement-exam clip from ordered speaker/voice segments."""

    normalized = [(str(text or "").strip(), str(voice or "").strip()) for text, voice in segments]
    normalized = [(text, voice) for text, voice in normalized if text]
    if not normalized or not settings.ENABLE_TTS:
        return None

    out_dir = Path(settings.UPLOAD_DIR) / "language_exam_audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"exam_{uuid.uuid4().hex}{language_tts_audio_extension()}"
    ok = await synthesize_language_speech_segments(
        normalized,
        language="en",
        output_path=dest,
    )
    if ok:
        return "/uploads/" + _storage_key(dest)

    combined = " ".join(text for text, _voice in normalized).strip()
    fallback_voice = normalized[0][1] if len({voice for _text, voice in normalized}) == 1 else None
    fallback = await _synthesize_openai_bytes(combined, voice=fallback_voice)
    if fallback is None:
        return None
    audio, ext = fallback
    dest = out_dir / f"exam_{uuid.uuid4().hex}.{ext}"
    dest.write_bytes(audio)
    return "/uploads/" + _storage_key(dest)


async def _cache_lookup(
    db: AsyncSession, *, content_item_id: int, teacher_id: int | None
) -> LanguageLessonAudioCache | None:
    query = select(LanguageLessonAudioCache).where(
        LanguageLessonAudioCache.content_item_id == content_item_id,
        LanguageLessonAudioCache.voice_source.in_(("supertonic", "openai")),
    )
    if teacher_id is not None:
        query = query.where(
            (LanguageLessonAudioCache.teacher_id == teacher_id)
            | (LanguageLessonAudioCache.teacher_id.is_(None))
        )
    result = await db.execute(query)
    rows = list(result.scalars().all())
    if not rows:
        return None
    rows.sort(key=lambda r: 0 if r.voice_source == "supertonic" else 1)
    return rows[0]


def _out(row: LanguageLessonAudioCache) -> dict:
    return {
        "public_url": row.public_url,
        "duration_seconds": row.duration_seconds,
        "voice_source": row.voice_source,
    }


def _is_legacy_supertonic_cache(row: LanguageLessonAudioCache) -> bool:
    if row.voice_source != "supertonic":
        return False
    return Path(row.audio_storage_key or "").name == f"supertonic{language_tts_audio_extension()}"


async def _upsert_cache(
    db: AsyncSession,
    *,
    content_item_id: int,
    voice_source: str,
    teacher_id: int | None,
    storage_key: str,
    public_url: str,
) -> LanguageLessonAudioCache:
    existing = await db.execute(
        select(LanguageLessonAudioCache).where(
            LanguageLessonAudioCache.content_item_id == content_item_id,
            LanguageLessonAudioCache.voice_source == voice_source,
            LanguageLessonAudioCache.teacher_id.is_(None)
            if teacher_id is None
            else LanguageLessonAudioCache.teacher_id == teacher_id,
        )
    )
    row = existing.scalar_one_or_none()
    if row is None:
        row = LanguageLessonAudioCache(
            content_item_id=content_item_id,
            voice_source=voice_source,
            teacher_id=teacher_id,
        )
        db.add(row)
    row.audio_storage_key = storage_key
    row.public_url = public_url
    row.duration_seconds = None
    await db.flush()
    return row


async def _synthesize_supertonic(
    db: AsyncSession,
    *,
    item: LanguageContentItem,
    text: str,
) -> dict | None:
    if not settings.ENABLE_TTS:
        return None

    voice_source = "supertonic"
    cache_teacher_id: int | None = None
    body = item.body_json if isinstance(item.body_json, dict) else {}
    listening_segments = (
        build_synthesis_segments(body)
        if item.skill == LanguageSkill.listening
        else []
    )
    fname = listening_cache_filename(listening_segments) if listening_segments else f"{voice_source}{language_tts_audio_extension()}"
    dest = _audio_dir(item.id) / fname

    if listening_segments:
        ok = await synthesize_listening_lesson_audio(body, language="en", output_path=dest)
    else:
        ok = await synthesize_language_speech(
            text,
            language="en",
            output_path=dest,
        )
    if not ok:
        return None

    storage_key = _storage_key(dest)
    public_url = "/uploads/" + storage_key
    row = await _upsert_cache(
        db,
        content_item_id=item.id,
        voice_source=voice_source,
        teacher_id=cache_teacher_id,
        storage_key=storage_key,
        public_url=public_url,
    )
    return _out(row)


def _openai_voice_for_exam_voice(voice: str | None) -> str:
    configured = (getattr(settings, "LANGUAGE_OPENAI_TTS_VOICE", None) or "").strip()
    raw = str(voice or "").strip().lower()
    if raw.startswith("m"):
        return "onyx"
    if raw.startswith("f"):
        return configured or "nova"
    return configured or "nova"


async def _synthesize_openai_bytes(text: str, *, voice: str | None = None) -> tuple[bytes, str] | None:
    api_key = (getattr(settings, "OPENAI_API_KEY", None) or "").strip()
    if not settings.ENABLE_TTS or not api_key:
        return None

    model = (getattr(settings, "SPEAKING_TTS_MODEL", None) or "gpt-4o-mini-tts").strip()
    openai_voice = _openai_voice_for_exam_voice(voice)
    timeout_raw = int(getattr(settings, "SPEAKING_TTS_TIMEOUT_SECONDS", 30) or 30)
    timeout_s = max(5, min(120, timeout_raw))
    payload = {
        "model": model,
        "voice": openai_voice,
        "input": text,
        "response_format": _OPENAI_AUDIO_FORMAT,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=float(timeout_s)) as client:
                response = await client.post(_OPENAI_SPEECH_URL, headers=headers, json=payload)
            if response.status_code == 429 and attempt == 0:
                await asyncio.sleep(1.2)
                continue
            response.raise_for_status()
            if response.content:
                return response.content, _OPENAI_AUDIO_FORMAT
        except Exception as exc:  # noqa: BLE001 - lesson audio is never load-bearing
            if attempt == 0:
                continue
            logger.warning("OpenAI lesson TTS fallback failed: %s", exc)
    return None


async def _synthesize_openai(
    db: AsyncSession,
    *,
    item: LanguageContentItem,
    text: str,
) -> dict | None:
    fallback = await _synthesize_openai_bytes(text)
    if fallback is None:
        return None
    audio, ext = fallback
    voice_source = "openai"
    cache_teacher_id: int | None = None
    dest = _audio_dir(item.id) / f"{voice_source}.{ext}"
    dest.write_bytes(audio)
    storage_key = _storage_key(dest)
    public_url = "/uploads/" + storage_key
    row = await _upsert_cache(
        db,
        content_item_id=item.id,
        voice_source=voice_source,
        teacher_id=cache_teacher_id,
        storage_key=storage_key,
        public_url=public_url,
    )
    return _out(row)


async def get_lesson_audio(db: AsyncSession, *, content_item_id: int, teacher_id: int | None = None) -> dict | None:
    cached = await _cache_lookup(db, content_item_id=content_item_id, teacher_id=teacher_id)
    if cached:
        disk_path = Path(settings.UPLOAD_DIR) / cached.audio_storage_key
        if disk_path.exists() and not _is_legacy_supertonic_cache(cached):
            return _out(cached)
    return await generate_lesson_audio(db, content_item_id=content_item_id, teacher_id=teacher_id)


async def generate_lesson_audio(
    db: AsyncSession, *, content_item_id: int, teacher_id: int | None = None
) -> dict | None:
    item = await db.get(LanguageContentItem, content_item_id)
    if not item:
        return None
    text = _lesson_text(item)
    if not text:
        return None

    supertonic = await _synthesize_supertonic(db, item=item, text=text)
    if supertonic is not None:
        return supertonic
    return await _synthesize_openai(db, item=item, text=text)
