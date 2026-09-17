"""Student lesson voice chat STT — Deepgram Nova (Arabic)."""

from __future__ import annotations

import asyncio
import logging
import mimetypes
from pathlib import Path

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_DEEPGRAM_LISTEN_URL = "https://api.deepgram.com/v1/listen"


def _deepgram_api_key() -> str:
    return (settings.DEEPGRAM_API_KEY or "").strip()


def _deepgram_model() -> str:
    return (settings.DEEPGRAM_STT_MODEL or "nova-3").strip()


def _content_type(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def _extract_transcript(payload: dict) -> str:
    channels = payload.get("results", {}).get("channels") or []
    if not channels:
        return ""
    alternatives = channels[0].get("alternatives") or []
    if not alternatives:
        return ""
    return str(alternatives[0].get("transcript") or "").strip()


def _transcribe_deepgram_sync(path: Path) -> str:
    api_key = _deepgram_api_key()
    if not api_key:
        raise RuntimeError("DEEPGRAM_API_KEY is not configured")

    model = _deepgram_model()
    audio_bytes = path.read_bytes()
    response = httpx.post(
        _DEEPGRAM_LISTEN_URL,
        headers={
            "Authorization": f"Token {api_key}",
            "Content-Type": _content_type(path),
        },
        params={
            "model": model,
            "language": "ar",
            "smart_format": "true",
        },
        content=audio_bytes,
        timeout=httpx.Timeout(120.0),
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Deepgram transcription failed: status={response.status_code} detail={response.text[:500]}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Deepgram transcription returned invalid JSON") from exc

    return _extract_transcript(payload)


async def _transcribe_gemini_fallback(path: Path) -> str:
    """Gemini fallback when Deepgram is unavailable — no faster-whisper on this path."""
    if not settings.GEMINI_API_KEY:
        return ""
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Browser recordings (.webm/.ogg/.m4a) are audio even though mimetypes maps
        # some containers to video/*; force an audio MIME so Gemini processes them.
        mime = mimetypes.guess_type(path.name)[0] or ""
        if not mime.startswith("audio/"):
            ext = path.suffix.lower().lstrip(".")
            mime = {
                "webm": "audio/webm",
                "ogg": "audio/ogg",
                "m4a": "audio/mp4",
                "mp4": "audio/mp4",
                "mp3": "audio/mpeg",
                "wav": "audio/wav",
            }.get(ext, "audio/webm")
        uploaded = await asyncio.to_thread(genai.upload_file, str(path), mime_type=mime)
        # Uploaded files must reach ACTIVE state before generate_content accepts them.
        for _ in range(60):
            file_info = await asyncio.to_thread(genai.get_file, uploaded.name)
            state_name = getattr(getattr(file_info, "state", None), "name", str(getattr(file_info, "state", "")))
            if state_name == "ACTIVE":
                uploaded = file_info
                break
            if state_name == "FAILED":
                raise RuntimeError(f"Gemini file processing failed: {uploaded.name}")
            await asyncio.sleep(1)
        else:
            raise RuntimeError(f"Gemini file not ACTIVE after wait: {uploaded.name}")
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = await asyncio.to_thread(
            model.generate_content,
            [
                "انسخ هذا التسجيل الصوتي بالعربية. أعد النص فقط بدون تعليقات.",
                uploaded,
            ],
            request_options={"timeout": 60},
        )
        return (response.text or "").strip()
    except Exception as exc:
        logger.warning("Student chat Gemini STT fallback failed: %s", exc)
        return ""


async def transcribe_student_chat_audio(audio_path: str | Path) -> str:
    """Transcribe a student lesson voice question (Arabic) via Deepgram Nova."""
    path = Path(audio_path)
    if not path.exists():
        return ""

    if _deepgram_api_key():
        try:
            text = await asyncio.to_thread(_transcribe_deepgram_sync, path)
            if text.strip():
                logger.info(
                    "Student chat STT engine=deepgram model=%s text_len=%s",
                    _deepgram_model(),
                    len(text),
                )
                return text
        except Exception as exc:
            logger.warning("Deepgram student chat transcription failed: %s", exc)
    else:
        logger.warning("DEEPGRAM_API_KEY missing — student chat STT falling back to Gemini")

    return await _transcribe_gemini_fallback(path)
