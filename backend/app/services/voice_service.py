"""Whisper transcription and teaching-style persona extraction."""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.services.model_cache import configure_model_cache
from app.services.ai_service import generate_ollama_text

logger = logging.getLogger(__name__)
settings = get_settings()

DEFAULT_PERSONA = """أنت معلم سوري ودود يشرح للطلاب باللهجة السورية المبسطة.
استخدم أمثلة من الحياة اليومية، اشرح خطوة بخطوة، وشجع الطالب.
لا تجب إلا من محتوى الدرس المرفوع. إذا السؤال خارج المحتوى قل ذلك بلطف."""

GEMINI_TRANSCRIBE_VIDEO_PROMPT = (
    "انسخ كل الكلام المنطوق في هذا الفيديو التعليمي بالعربية. "
    "أعد النص الكامل فقط دون أي تعليقات أو تنسيق إضافي."
)

_whisper_model = None
_lesson_faster_whisper_model = None

# Map Whisper names to multilingual faster-whisper ids (never .en for Syria).
_FASTER_WHISPER_MODEL_ALIASES: dict[str, str] = {
    "turbo": "large-v3-turbo",
    "large-v3-turbo": "large-v3-turbo",
    "whisper-large-v3-turbo": "large-v3-turbo",
    "large": "large-v3",
    "medium": "medium",
    "small": "small",
    "base": "base",
    "tiny": "tiny",
}


@dataclass
class VideoTranscriptionResult:
    text: str
    engine: str
    model: str
    duration_s: float
    fallback_reason: str | None = None


def _find_ffmpeg_executable() -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        logger.warning("FFmpeg executable not found; install imageio-ffmpeg or system ffmpeg: %s", exc)
        return None


def _load_audio_mono_16k(path: Path):
    """Decode any supported audio file to a mono 16 kHz float32 numpy array."""
    ffmpeg = _find_ffmpeg_executable()
    if not ffmpeg:
        raise RuntimeError("ffmpeg not available")

    import numpy as np

    result = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-f",
            "f32le",
            "-acodec",
            "pcm_f32le",
            "-ac",
            "1",
            "-ar",
            "16000",
            "pipe:1",
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout:
        error = (result.stderr or result.stdout or b"").decode("utf-8", errors="replace")[-500:]
        raise RuntimeError(f"ffmpeg audio decode failed: {error}")
    return np.frombuffer(result.stdout, dtype=np.float32).copy(), 16000


def _lesson_whisper_language() -> str:
    return (settings.LESSON_VIDEO_WHISPER_LANGUAGE or "ar").strip() or "ar"


def _faster_whisper_model_id() -> str:
    if settings.WHISPER_MODEL_PATH.strip():
        return settings.WHISPER_MODEL_PATH.strip()
    configured = (settings.WHISPER_MODEL or "turbo").strip()
    return _FASTER_WHISPER_MODEL_ALIASES.get(configured, configured)


def _lesson_faster_whisper_model_id() -> str:
    override = (settings.LESSON_VIDEO_FASTER_WHISPER_MODEL or "").strip()
    if override:
        return override
    return _faster_whisper_model_id()


def _get_lesson_faster_whisper_model():
    global _lesson_faster_whisper_model
    if _lesson_faster_whisper_model is not None:
        return _lesson_faster_whisper_model

    configure_model_cache()

    from faster_whisper import WhisperModel

    model_id = _lesson_faster_whisper_model_id()
    logger.info("Loading faster-whisper model for lesson video: %s", model_id)
    _lesson_faster_whisper_model = WhisperModel(model_id, device="cpu", compute_type="int8")
    return _lesson_faster_whisper_model


def _extract_video_to_wav(video_path: Path) -> Path:
    """Extract mono 16 kHz PCM wav from video; close handle before ffmpeg (Windows-safe)."""
    ffmpeg = _find_ffmpeg_executable()
    if not ffmpeg:
        raise RuntimeError("ffmpeg not available")

    fd, wav_name = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    wav_path = Path(wav_name)
    try:
        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(video_path),
                "-ar",
                "16000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(wav_path),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not wav_path.exists() or wav_path.stat().st_size == 0:
            raise RuntimeError(f"ffmpeg audio extract failed: {(result.stderr or result.stdout)[-400:]}")
        return wav_path
    except Exception:
        _safe_unlink(wav_path)
        raise


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Could not delete temp file %s: %s", path, exc)


def _transcribe_wav_faster_whisper(wav_path: Path) -> str:
    model = _get_lesson_faster_whisper_model()
    language = _lesson_whisper_language()
    segments, _info = model.transcribe(
        str(wav_path),
        language=language,
        beam_size=5,
        vad_filter=False,
    )
    return "".join(s.text for s in segments).strip()


def _log_video_transcription(result: VideoTranscriptionResult, *, path: Path) -> None:
    logger.info(
        "Lesson video transcription engine=%s model=%s duration_s=%.2f chars=%s path=%s fallback_reason=%s",
        result.engine,
        result.model,
        result.duration_s,
        len(result.text),
        path.name,
        result.fallback_reason or "none",
    )


def _transcribe_lesson_video_whisper_sync(video_path: Path) -> VideoTranscriptionResult | None:
    """Try faster-whisper. Returns empty result when Gemini fallback is needed."""
    started = time.perf_counter()
    wav_path: Path | None = None
    last_reason = "whisper_disabled"

    if not settings.ENABLE_WHISPER:
        return None

    try:
        wav_path = _extract_video_to_wav(video_path)

        try:
            text = _transcribe_wav_faster_whisper(wav_path)
            if text.strip():
                return VideoTranscriptionResult(
                    text=text.strip(),
                    engine="faster-whisper",
                    model=_lesson_faster_whisper_model_id(),
                    duration_s=time.perf_counter() - started,
                    fallback_reason=None,
                )
            last_reason = "faster_whisper_empty"
        except ImportError as exc:
            last_reason = f"faster_whisper_unavailable:{exc}"
            logger.warning("faster-whisper unavailable — %s", exc)
        except Exception as exc:
            last_reason = f"faster_whisper_failed:{exc}"
            logger.warning("faster-whisper lesson video transcription failed: %s", exc)

        return VideoTranscriptionResult(
            text="",
            engine="none",
            model="",
            duration_s=time.perf_counter() - started,
            fallback_reason=last_reason,
        )
    finally:
        if wav_path is not None:
            _safe_unlink(wav_path)


def _gemini_fallback_allowed(provider_name: str) -> bool:
    if settings.VIDEO_TRANSCRIPTION_ALLOW_GEMINI_FALLBACK:
        return bool(settings.GEMINI_API_KEY)
    # Rollback whisper path keeps the historical whisper → Gemini behavior.
    if provider_name in {"whisper", "faster-whisper", "faster_whisper"}:
        return bool(settings.GEMINI_API_KEY)
    return False


async def _try_gemini_video_fallback(
    path: Path,
    *,
    started: float,
    fallback_reason: str | None,
) -> str | None:
    if not settings.GEMINI_API_KEY:
        return None
    timeout_s = int(settings.LESSON_VIDEO_GEMINI_TIMEOUT_SECONDS or 600)
    try:
        text = await _transcribe_video_with_gemini(path, timeout_s=timeout_s)
        if text.strip():
            result = VideoTranscriptionResult(
                text=text.strip(),
                engine="gemini",
                model=settings.GEMINI_MODEL,
                duration_s=time.perf_counter() - started,
                fallback_reason=fallback_reason,
            )
            _log_video_transcription(result, path=path)
            return result.text
    except Exception:
        logger.warning("Gemini lesson video transcription failed")
    return None


async def transcribe_lesson_video(
    video_path: str | Path,
    *,
    language_hint: str | None = None,
    locale: str | None = None,
    subject: str | None = None,
    keyterms: list[str] | None = None,
) -> str:
    """Transcribe uploaded lesson video audio into lesson text.

    Default provider is Deepgram Nova-3 (``VIDEO_TRANSCRIPTION_PROVIDER=deepgram``).
    Whisper / Gemini run only when explicitly selected or fallback flags are enabled.
    Does not affect Speaking, placement, teacher voice-sample, or student-chat STT.
    """
    from app.services.video_transcription.errors import (
        CATEGORY_EMPTY_AUDIO,
        VideoTranscriptionError,
        user_message_for,
    )
    from app.services.video_transcription.factory import get_video_transcription_provider
    from app.services.video_transcription.language import resolve_video_transcription_language

    path = Path(video_path)
    if not path.exists():
        return ""

    started = time.perf_counter()
    provider_name = (settings.VIDEO_TRANSCRIPTION_PROVIDER or "deepgram").strip().lower()
    language = resolve_video_transcription_language(
        locale=locale,
        language_hint=language_hint,
        subject=subject,
    )
    wav_path: Path | None = None
    primary_error: VideoTranscriptionError | None = None
    fallback_reason: str | None = None

    try:
        try:
            wav_path = await asyncio.to_thread(_extract_video_to_wav, path)
        except Exception as exc:
            raise VideoTranscriptionError(
                user_message_for(CATEGORY_EMPTY_AUDIO),
                category=CATEGORY_EMPTY_AUDIO,
                provider=provider_name,
            ) from exc

        if not wav_path.exists() or wav_path.stat().st_size == 0:
            raise VideoTranscriptionError(
                user_message_for(CATEGORY_EMPTY_AUDIO),
                category=CATEGORY_EMPTY_AUDIO,
                provider=provider_name,
            )

        primary = get_video_transcription_provider(provider_name)
        try:
            transcript = await primary.transcribe(
                wav_path,
                language=language,
                mime_type="audio/wav",
                keyterms=keyterms,
            )
            text = transcript.normalized_text()
            if text:
                _log_video_transcription(
                    VideoTranscriptionResult(
                        text=text,
                        engine=transcript.provider,
                        model=transcript.model,
                        duration_s=time.perf_counter() - started,
                    ),
                    path=path,
                )
                return text
            fallback_reason = f"{primary.name}_empty"
        except VideoTranscriptionError as exc:
            primary_error = exc
            fallback_reason = f"{exc.provider or primary.name}:{exc.category}"
            logger.warning(
                "Lesson video primary STT failed provider=%s category=%s",
                exc.provider or primary.name,
                exc.category,
            )

        # Explicit Whisper fallback for Deepgram only when the flag is set.
        if (
            primary.name == "deepgram"
            and settings.VIDEO_TRANSCRIPTION_ALLOW_WHISPER_FALLBACK
            and settings.ENABLE_WHISPER
        ):
            try:
                whisper_provider = get_video_transcription_provider("whisper")
                transcript = await whisper_provider.transcribe(
                    wav_path,
                    language=language,
                    mime_type="audio/wav",
                )
                text = transcript.normalized_text()
                if text:
                    _log_video_transcription(
                        VideoTranscriptionResult(
                            text=text,
                            engine=transcript.provider,
                            model=transcript.model,
                            duration_s=time.perf_counter() - started,
                            fallback_reason=fallback_reason,
                        ),
                        path=path,
                    )
                    return text
                fallback_reason = f"{fallback_reason};whisper_empty"
            except VideoTranscriptionError as whisper_exc:
                fallback_reason = f"{fallback_reason};whisper:{whisper_exc.category}"

        if _gemini_fallback_allowed(primary.name):
            gemini_text = await _try_gemini_video_fallback(
                path, started=started, fallback_reason=fallback_reason
            )
            if gemini_text:
                return gemini_text
            fallback_reason = f"{fallback_reason};gemini_empty_or_failed"

        if primary_error is not None:
            raise primary_error

        result = VideoTranscriptionResult(
            text="",
            engine="none",
            model="",
            duration_s=time.perf_counter() - started,
            fallback_reason=fallback_reason or "empty_transcript",
        )
        _log_video_transcription(result, path=path)
        return ""
    finally:
        if wav_path is not None:
            _safe_unlink(wav_path)



async def _transcribe_video_with_gemini(path: Path, *, timeout_s: int) -> str:
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    uploaded = await asyncio.to_thread(genai.upload_file, str(path))
    for _ in range(60):
        file_info = await asyncio.to_thread(genai.get_file, uploaded.name)
        state = getattr(file_info, "state", None)
        state_name = getattr(state, "name", str(state))
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
        [GEMINI_TRANSCRIBE_VIDEO_PROMPT, uploaded],
        request_options={"timeout": timeout_s},
    )
    return (response.text or "").strip()


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    configure_model_cache()

    from faster_whisper import WhisperModel

    model_id = _faster_whisper_model_id()
    logger.info("Loading faster-whisper model for Arabic STT: %s", model_id)
    _whisper_model = WhisperModel(model_id, device="cpu", compute_type="int8")
    return _whisper_model


async def transcribe_audio(audio_path: str | Path) -> str:
    path = Path(audio_path)
    if not path.exists():
        return ""

    if settings.ENABLE_WHISPER:
        try:
            return await asyncio.to_thread(_transcribe_with_whisper_sync, path)
        except Exception as exc:
            logger.warning("Whisper transcription failed: %s", exc)

    if settings.GEMINI_API_KEY:
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.GEMINI_API_KEY)
            # Force an audio MIME so browser recordings (.webm/.ogg/.m4a) aren't
            # misdetected as video/* and rejected by Gemini file processing.
            _mime = mimetypes.guess_type(Path(path).name)[0] or ""
            if not _mime.startswith("audio/"):
                _ext = Path(path).suffix.lower().lstrip(".")
                _mime = {
                    "webm": "audio/webm",
                    "ogg": "audio/ogg",
                    "m4a": "audio/mp4",
                    "mp4": "audio/mp4",
                    "mp3": "audio/mpeg",
                    "wav": "audio/wav",
                }.get(_ext, "audio/webm")
            uploaded = await asyncio.to_thread(genai.upload_file, str(path), mime_type=_mime)
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
            logger.warning("Gemini transcription failed: %s", exc)

    return ""


def _transcribe_with_whisper_sync(path: Path) -> str:
    model = _get_whisper_model()
    segments, _info = model.transcribe(
        str(path),
        language="ar",
        beam_size=5,
        vad_filter=False,
    )
    return "".join(segment.text for segment in segments).strip()


async def build_persona_prompt(transcript: str, subject: str, grade: str) -> str:
    if transcript and settings.LLM_PROVIDER.lower() == "ollama":
        try:
            prompt = f"""Analyze this teacher transcript and write a concise persona prompt in Arabic.
The persona should guide an AI tutor to explain in the same friendly Syrian Arabic style.
Return JSON only:
{{"persona": "..."}}

Subject: {subject}
Grade: {grade}

Teacher transcript:
{transcript[:3000]}
"""
            text = await generate_ollama_text(prompt, temperature=0.1)
            if "{" in text and "}" in text:
                data = json.loads(text[text.index("{") : text.rindex("}") + 1])
                persona = data.get("persona")
                if persona:
                    return persona
        except Exception as exc:
            logger.warning("Ollama persona generation failed: %s", exc)

    from app.services.claude_service import generate_claude_text, is_claude_configured

    if is_claude_configured() and transcript:
        try:
            prompt = f"""حلل أسلوب هذا المعلم من النص الصوتي واكتب Persona Prompt بالعربية لتوجيه ذكاء اصطناعي
للشرح بنفس الأسلوب واللهجة السورية. المادة: {subject}، الصف: {grade}.

نص المعلم:
{transcript[:3000]}

أعد JSON فقط بالشكل:
{{"persona": "..."}}"""
            text = await generate_claude_text(prompt, temperature=0.1, max_tokens=1024, timeout=20.0)
            if "{" in text:
                data = json.loads(text[text.index("{") : text.rindex("}") + 1])
                return data.get("persona", DEFAULT_PERSONA)
        except Exception as exc:
            logger.warning("Persona generation failed: %s", exc)

    style_hint = f"\n\nالمادة: {subject}، الصف: {grade}."
    if transcript:
        style_hint += f"\nاستفد من عينة صوت المعلم هذه: {transcript[:500]}"
    return f"{DEFAULT_PERSONA}{style_hint}"
