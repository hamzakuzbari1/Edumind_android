"""Deepgram Nova pre-recorded STT for uploaded lesson videos."""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import time
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.services.video_transcription.base import TranscriptionProvider
from app.services.video_transcription.errors import (
    CATEGORY_EMPTY_AUDIO,
    CATEGORY_EMPTY_TRANSCRIPT,
    CATEGORY_MALFORMED_RESPONSE,
    CATEGORY_MISSING_API_KEY,
    CATEGORY_NETWORK,
    CATEGORY_TIMEOUT,
    CATEGORY_UNKNOWN,
    VideoTranscriptionError,
    error_from_http_status,
    user_message_for,
)
from app.services.video_transcription.types import TranscriptResult, TranscriptSegment

logger = logging.getLogger(__name__)

_DEEPGRAM_LISTEN_URL = "https://api.deepgram.com/v1/listen"
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = (1.0, 2.0, 4.0)


def _content_type(path: Path, override: str | None = None) -> str:
    if override:
        return override
    guessed = mimetypes.guess_type(path.name)[0]
    if guessed:
        return guessed
    ext = path.suffix.lower()
    return {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".webm": "audio/webm",
        ".flac": "audio/flac",
    }.get(ext, "application/octet-stream")


def _safe_keyterms(keyterms: list[str] | None, *, limit: int = 50) -> list[str]:
    if not keyterms:
        return []
    cleaned: list[str] = []
    for term in keyterms:
        value = " ".join(str(term).split()).strip()
        if not value or len(value) > 100:
            continue
        cleaned.append(value)
        if len(cleaned) >= limit:
            break
    return cleaned


def _map_deepgram_payload(payload: dict, *, language: str, model: str, started: float) -> TranscriptResult:
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, dict):
        raise VideoTranscriptionError(
            user_message_for(CATEGORY_MALFORMED_RESPONSE),
            category=CATEGORY_MALFORMED_RESPONSE,
            provider="deepgram",
        )

    channels = results.get("channels") or []
    if not channels:
        raise VideoTranscriptionError(
            user_message_for(CATEGORY_MALFORMED_RESPONSE),
            category=CATEGORY_MALFORMED_RESPONSE,
            provider="deepgram",
        )

    alternatives = channels[0].get("alternatives") or []
    if not alternatives:
        raise VideoTranscriptionError(
            user_message_for(CATEGORY_MALFORMED_RESPONSE),
            category=CATEGORY_MALFORMED_RESPONSE,
            provider="deepgram",
        )

    primary = alternatives[0] or {}
    text = str(primary.get("transcript") or "").strip()

    segments: list[TranscriptSegment] = []
    paragraphs = primary.get("paragraphs") or {}
    para_list = paragraphs.get("paragraphs") if isinstance(paragraphs, dict) else None
    if isinstance(para_list, list):
        for para in para_list:
            if not isinstance(para, dict):
                continue
            sentences = para.get("sentences") or []
            parts: list[str] = []
            start = para.get("start")
            end = para.get("end")
            if isinstance(sentences, list):
                for sentence in sentences:
                    if isinstance(sentence, dict):
                        st = str(sentence.get("text") or "").strip()
                        if st:
                            parts.append(st)
            joined = " ".join(parts).strip()
            if joined:
                segments.append(
                    TranscriptSegment(
                        text=joined,
                        start=float(start) if isinstance(start, (int, float)) else None,
                        end=float(end) if isinstance(end, (int, float)) else None,
                    )
                )

    if not text and segments:
        text = "\n\n".join(seg.text for seg in segments).strip()

    if not text:
        raise VideoTranscriptionError(
            user_message_for(CATEGORY_EMPTY_TRANSCRIPT),
            category=CATEGORY_EMPTY_TRANSCRIPT,
            provider="deepgram",
        )

    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    audio_duration = metadata.get("duration")
    audio_duration_s = float(audio_duration) if isinstance(audio_duration, (int, float)) else None

    return TranscriptResult(
        text=text,
        provider="deepgram",
        model=model,
        language=language,
        duration_s=time.perf_counter() - started,
        audio_duration_s=audio_duration_s,
        segments=tuple(segments),
        status="ok",
    )


class DeepgramTranscriptionProvider(TranscriptionProvider):
    """Pre-recorded Deepgram Speech-to-Text (Nova-3) for lesson videos."""

    @property
    def name(self) -> str:
        return "deepgram"

    async def transcribe(
        self,
        audio_path: Path,
        *,
        language: str,
        mime_type: str | None = None,
        keyterms: list[str] | None = None,
    ) -> TranscriptResult:
        return await asyncio.to_thread(
            self._transcribe_sync,
            audio_path,
            language=language,
            mime_type=mime_type,
            keyterms=keyterms,
        )

    def _transcribe_sync(
        self,
        audio_path: Path,
        *,
        language: str,
        mime_type: str | None,
        keyterms: list[str] | None,
    ) -> TranscriptResult:
        settings = get_settings()
        api_key = (settings.DEEPGRAM_API_KEY or "").strip()
        if not api_key:
            raise VideoTranscriptionError(
                user_message_for(CATEGORY_MISSING_API_KEY),
                category=CATEGORY_MISSING_API_KEY,
                provider=self.name,
            )

        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise VideoTranscriptionError(
                user_message_for(CATEGORY_EMPTY_AUDIO),
                category=CATEGORY_EMPTY_AUDIO,
                provider=self.name,
            )

        model = (settings.DEEPGRAM_STT_MODEL or "nova-3").strip() or "nova-3"
        timeout_s = float(settings.DEEPGRAM_STT_TIMEOUT_SECONDS or 300)
        smart_format = bool(settings.DEEPGRAM_STT_SMART_FORMAT)
        audio_bytes = audio_path.read_bytes()
        content_type = _content_type(audio_path, mime_type)
        terms = _safe_keyterms(keyterms)

        params: list[tuple[str, str]] = [
            ("model", model),
            ("language", language),
            ("smart_format", "true" if smart_format else "false"),
            ("punctuate", "true"),
            ("paragraphs", "true"),
        ]
        for term in terms:
            params.append(("keyterm", term))

        started = time.perf_counter()
        last_error: VideoTranscriptionError | None = None

        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = httpx.post(
                    _DEEPGRAM_LISTEN_URL,
                    headers={
                        "Authorization": f"Token {api_key}",
                        "Content-Type": content_type,
                    },
                    params=params,
                    content=audio_bytes,
                    timeout=httpx.Timeout(timeout_s),
                )
            except httpx.TimeoutException as exc:
                last_error = VideoTranscriptionError(
                    user_message_for(CATEGORY_TIMEOUT),
                    category=CATEGORY_TIMEOUT,
                    retryable=True,
                    provider=self.name,
                )
                logger.warning(
                    "Deepgram video STT timeout attempt=%s/%s provider=deepgram model=%s",
                    attempt + 1,
                    _MAX_ATTEMPTS,
                    model,
                )
                if attempt + 1 >= _MAX_ATTEMPTS:
                    raise last_error from exc
                time.sleep(_BACKOFF_SECONDS[min(attempt, len(_BACKOFF_SECONDS) - 1)])
                continue
            except httpx.HTTPError as exc:
                last_error = VideoTranscriptionError(
                    user_message_for(CATEGORY_NETWORK),
                    category=CATEGORY_NETWORK,
                    retryable=True,
                    provider=self.name,
                )
                logger.warning(
                    "Deepgram video STT network failure attempt=%s/%s",
                    attempt + 1,
                    _MAX_ATTEMPTS,
                )
                if attempt + 1 >= _MAX_ATTEMPTS:
                    raise last_error from exc
                time.sleep(_BACKOFF_SECONDS[min(attempt, len(_BACKOFF_SECONDS) - 1)])
                continue

            status = response.status_code
            if status >= 400:
                err = error_from_http_status(status, provider=self.name)
                logger.warning(
                    "Deepgram video STT http_status=%s category=%s attempt=%s/%s model=%s",
                    status,
                    err.category,
                    attempt + 1,
                    _MAX_ATTEMPTS,
                    model,
                )
                if err.retryable and attempt + 1 < _MAX_ATTEMPTS:
                    last_error = err
                    time.sleep(_BACKOFF_SECONDS[min(attempt, len(_BACKOFF_SECONDS) - 1)])
                    continue
                raise err

            try:
                payload = response.json()
            except ValueError as exc:
                raise VideoTranscriptionError(
                    user_message_for(CATEGORY_MALFORMED_RESPONSE),
                    category=CATEGORY_MALFORMED_RESPONSE,
                    provider=self.name,
                ) from exc

            if not isinstance(payload, dict):
                raise VideoTranscriptionError(
                    user_message_for(CATEGORY_MALFORMED_RESPONSE),
                    category=CATEGORY_MALFORMED_RESPONSE,
                    provider=self.name,
                )

            result = _map_deepgram_payload(payload, language=language, model=model, started=started)
            logger.info(
                "Lesson video STT provider=deepgram model=%s language=%s "
                "audio_duration_s=%s processing_duration_s=%.2f chars=%s http_status=%s",
                model,
                language,
                result.audio_duration_s,
                result.duration_s or 0.0,
                len(result.text),
                status,
            )
            return result

        if last_error:
            raise last_error
        raise VideoTranscriptionError(
            user_message_for(CATEGORY_UNKNOWN),
            category=CATEGORY_UNKNOWN,
            provider=self.name,
        )
