"""English speech-to-text for the Language module — OpenAI GPT-4o Transcribe with Whisper fallback."""

from __future__ import annotations

import asyncio
import logging
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.services.model_cache import configure_model_cache

logger = logging.getLogger(__name__)
settings = get_settings()

_conversation_whisper_model = None
_OPENAI_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"


class AudioDecoderError(RuntimeError):
    """Base class for safe, externally classifiable decoder failures."""

    code = "invalid_audio"


class AudioDecoderUnavailable(AudioDecoderError):
    code = "decoder_unavailable"


class AudioDecoderTimeout(AudioDecoderError):
    code = "decoder_timeout"


class InvalidAudio(AudioDecoderError):
    code = "invalid_audio"


class TranscriptionUnavailable(RuntimeError):
    """The configured STT provider could not produce an authoritative result."""

    code = "stt_unavailable"

DEFAULT_INITIAL_PROMPT = (
    "English language placement interview. Transcribe only words actually spoken in the recording. "
    "Do not infer an answer from silence, noise, music, or the interview context."
)

_COMMON_STT_HALLUCINATIONS = {
    "thank you",
    "thank you very much",
    "thanks for watching",
    "please subscribe",
    "like and subscribe",
    "music",
}


@dataclass
class ConversationTranscription:
    text: str
    engine: str
    model: str
    duration_s: float = 0.0
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    language_probability: float | None = None
    low_confidence: bool = False
    raw_text: str = ""
    meta: dict = field(default_factory=dict)


def _language_stt_provider() -> str:
    return (settings.LANGUAGE_STT_PROVIDER or "openai").strip().lower()


def _openai_api_key() -> str:
    return (settings.OPENAI_API_KEY or "").strip()


def _language_stt_model() -> str:
    return (settings.LANGUAGE_STT_MODEL or "gpt-4o-transcribe").strip()


def _should_use_openai_stt() -> bool:
    return _language_stt_provider() == "openai" and bool(_openai_api_key())


def _allow_whisper_fallback() -> bool:
    return bool(settings.LANGUAGE_STT_ALLOW_WHISPER_FALLBACK)


def _resolve_ffmpeg() -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _normalize_to_wav_16k(source: Path) -> Path:
    """Decode browser webm/opus to mono 16 kHz wav — required for reliable Whisper accuracy."""
    ffmpeg = _resolve_ffmpeg()
    if not ffmpeg:
        raise AudioDecoderUnavailable("Audio decoder is unavailable")

    fd, out_name = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    out = Path(out_name)
    cmd = [
        ffmpeg,
        "-nostdin",
        "-v",
        "error",
        "-y",
        "-i",
        str(source),
        # Bound decoded output as well as wall-clock time.  Placement validation rejects anything
        # above 180 seconds; stopping at 181 keeps a compressed hours-long upload from expanding
        # without bound before that duration check can run.
        "-t",
        str(max(1, int(getattr(settings, "LANGUAGE_AUDIO_DECODE_MAX_SECONDS", 181)))),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(out),
    ]
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            stdout, stderr = process.communicate(
                timeout=max(1, int(settings.LANGUAGE_FFMPEG_TIMEOUT_SECONDS))
            )
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.communicate()
            raise AudioDecoderTimeout("Audio decoding timed out") from exc
    except AudioDecoderError:
        out.unlink(missing_ok=True)
        raise
    except OSError as exc:
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate()
        out.unlink(missing_ok=True)
        raise AudioDecoderUnavailable("Audio decoder could not be started") from exc
    except Exception as exc:
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate()
        out.unlink(missing_ok=True)
        raise InvalidAudio("Audio file is corrupt or cannot be decoded") from exc

    if process.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        # Do not propagate ffmpeg output: filenames and decoder details are not safe API/log data.
        _ = stdout, stderr
        out.unlink(missing_ok=True)
        raise InvalidAudio("Audio file is corrupt or cannot be decoded")
    return out


def _get_conversation_whisper_model():
    global _conversation_whisper_model
    if _conversation_whisper_model is not None:
        return _conversation_whisper_model

    configure_model_cache()

    from faster_whisper import WhisperModel

    model_id = (settings.LANGUAGE_CONVERSATION_WHISPER_MODEL or "small.en").strip()
    compute = (settings.LANGUAGE_CONVERSATION_WHISPER_COMPUTE_TYPE or "float32").strip()
    logger.info(
        "Loading conversation faster-whisper model=%s compute_type=%s device=cpu",
        model_id,
        compute,
    )
    _conversation_whisper_model = WhisperModel(model_id, device="cpu", compute_type=compute)
    return _conversation_whisper_model


def _initial_prompt() -> str:
    raw = (settings.LANGUAGE_CONVERSATION_WHISPER_INITIAL_PROMPT or "").strip()
    return raw or DEFAULT_INITIAL_PROMPT


def _segment_confidence(segments: list) -> tuple[float | None, float | None]:
    if not segments:
        return None, None
    logprobs = [s.avg_logprob for s in segments if getattr(s, "avg_logprob", None) is not None]
    no_speech = [s.no_speech_prob for s in segments if getattr(s, "no_speech_prob", None) is not None]
    avg_logprob = sum(logprobs) / len(logprobs) if logprobs else None
    max_no_speech = max(no_speech) if no_speech else None
    return avg_logprob, max_no_speech


def _is_low_confidence(avg_logprob: float | None, no_speech_prob: float | None) -> bool:
    if no_speech_prob is not None and no_speech_prob >= 0.55:
        return True
    if avg_logprob is not None and avg_logprob <= -0.85:
        return True
    return False


def _transcript_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text.lower())


def classify_transcript_evidence(
    text: str,
    *,
    duration_s: float = 0.0,
    no_speech_prob: float | None = None,
    language_probability: float | None = None,
    provider_low_confidence: bool = False,
) -> tuple[str, str | None]:
    """Conservatively classify whether an English transcript is gradeable.

    This is deliberately a rejection gate, not speaker verification. It catches empty/very thin,
    high-no-speech, clearly non-English and pathological repetition evidence. A passing result only
    means there is enough server-produced text to continue; it does not prove who spoke.
    """
    normalized = (text or "").strip()
    words = _transcript_words(normalized)
    if not normalized:
        return "retry_required", "no_speech"
    alphabetic = [char for char in normalized if char.isalpha()]
    latin = [char for char in alphabetic if "a" <= char.lower() <= "z"]
    if len(alphabetic) >= 4 and len(latin) / len(alphabetic) < 0.75:
        return "retry_required", "wrong_language"
    if not words:
        return "retry_required", "no_speech"
    if " ".join(words) in _COMMON_STT_HALLUCINATIONS:
        return "retry_required", "possible_stt_hallucination"
    if len(words) < 3:
        return "retry_required", "insufficient_speech"
    if no_speech_prob is not None and no_speech_prob >= 0.55:
        return "retry_required", "no_speech"
    if provider_low_confidence:
        return "retry_required", "low_confidence_speech"

    # A long recording with only a couple of recognized words is not reliable grading evidence.
    if duration_s >= 8.0 and len(words) < max(3, math.ceil(duration_s * 0.25)):
        return "retry_required", "insufficient_speech"

    if len(words) >= 3 and len(set(words)) == 1:
        return "retry_required", "repetitive_speech"
    if len(words) >= 6:
        most_common = max(words.count(word) for word in set(words))
        unique_ratio = len(set(words)) / len(words)
        if most_common / len(words) >= 0.7 or unique_ratio <= 0.2:
            return "retry_required", "repetitive_speech"

    if language_probability is not None and language_probability < 0.45:
        return "retry_required", "wrong_language"
    return "completed", None


def apply_transcript_evidence_gate(
    result: ConversationTranscription,
    *,
    audio_duration_s: float | None = None,
) -> ConversationTranscription:
    """Attach a structured evidence decision without inventing a score or transcript."""
    status, reason = classify_transcript_evidence(
        result.text,
        duration_s=float(audio_duration_s if audio_duration_s is not None else result.duration_s or 0.0),
        no_speech_prob=result.no_speech_prob,
        language_probability=result.language_probability,
        provider_low_confidence=result.low_confidence,
    )
    result.meta["evidence_status"] = status
    if reason:
        result.meta["rejection_code"] = reason
        result.low_confidence = True
    return result


def _transcribe_faster_whisper(wav_path: Path) -> ConversationTranscription:
    model = _get_conversation_whisper_model()
    model_id = (settings.LANGUAGE_CONVERSATION_WHISPER_MODEL or "small.en").strip()
    beam = max(1, int(settings.LANGUAGE_CONVERSATION_WHISPER_BEAM_SIZE or 5))
    vad = bool(settings.LANGUAGE_CONVERSATION_WHISPER_VAD)

    segments, info = model.transcribe(
        str(wav_path),
        language="en",
        beam_size=beam,
        best_of=beam,
        vad_filter=vad,
        initial_prompt=_initial_prompt(),
        condition_on_previous_text=False,
    )
    seg_list = list(segments)
    text = "".join(s.text for s in seg_list).strip()
    avg_logprob, no_speech_prob = _segment_confidence(seg_list)
    detected_language_probability = getattr(info, "language_probability", None)

    return ConversationTranscription(
        text=text,
        raw_text=text,
        engine="faster-whisper",
        model=model_id,
        duration_s=float(info.duration or 0.0),
        avg_logprob=avg_logprob,
        no_speech_prob=no_speech_prob,
        language_probability=(
            float(detected_language_probability)
            if detected_language_probability is not None
            else None
        ),
        low_confidence=_is_low_confidence(avg_logprob, no_speech_prob),
        meta={
            "beam_size": beam,
            "vad_filter": vad,
            "compute_type": settings.LANGUAGE_CONVERSATION_WHISPER_COMPUTE_TYPE,
            "segment_count": len(seg_list),
            "fallback": True,
        },
    )


def _transcribe_openai(source_path: Path) -> ConversationTranscription:
    """Transcribe with OpenAI Audio API (gpt-4o-transcribe)."""
    api_key = _openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    model = _language_stt_model()
    prompt = _initial_prompt()

    with source_path.open("rb") as audio_file:
        response = httpx.post(
            _OPENAI_TRANSCRIPTIONS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (source_path.name, audio_file, "application/octet-stream")},
            data={
                "model": model,
                "language": "en",
                "response_format": "json",
                "prompt": prompt,
            },
            timeout=httpx.Timeout(120.0),
        )

    if response.status_code >= 400:
        raise TranscriptionUnavailable(
            f"OpenAI transcription failed with HTTP status {response.status_code}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise TranscriptionUnavailable("OpenAI transcription returned invalid JSON") from exc

    text = str(payload.get("text") or "").strip()
    return ConversationTranscription(
        text=text,
        raw_text=text,
        engine="openai",
        model=model,
        low_confidence=not text,
        meta={"provider": "openai", "fallback": False},
    )


def _transcribe_whisper_sync(source_path: Path) -> ConversationTranscription:
    wav_path: Path | None = None
    try:
        wav_path = _normalize_to_wav_16k(source_path)
        result = _transcribe_faster_whisper(wav_path)
        result.meta["normalized_wav"] = True
        return result
    finally:
        if wav_path and wav_path.exists():
            try:
                wav_path.unlink()
            except OSError:
                pass


def _transcribe_sync(source_path: Path) -> tuple[ConversationTranscription, float]:
    started = time.perf_counter()

    if _should_use_openai_stt():
        try:
            result = _transcribe_openai(source_path)
            elapsed = time.perf_counter() - started
            return result, elapsed
        except Exception as exc:
            if not _allow_whisper_fallback():
                raise RuntimeError(
                    f"OpenAI language STT failed and Whisper fallback is disabled: {exc}"
                ) from exc
            logger.warning("OpenAI language STT failed; using local fallback error_type=%s", type(exc).__name__)

    if not _allow_whisper_fallback():
        raise RuntimeError("Language STT unavailable: OpenAI is not configured and Whisper fallback is disabled")

    if not settings.ENABLE_WHISPER:
        raise RuntimeError("Language STT unavailable: OpenAI failed and Whisper is disabled")

    result = _transcribe_whisper_sync(source_path)
    elapsed = time.perf_counter() - started
    return result, elapsed


async def transcribe_english_audio(
    data: bytes,
    *,
    suffix: str = ".webm",
    audio_duration_s: float | None = None,
) -> ConversationTranscription:
    """Transcribe uploaded audio to English text with confidence metadata."""
    if not data:
        return ConversationTranscription(text="", raw_text="", engine="none", model="")

    if not _should_use_openai_stt() and not settings.ENABLE_WHISPER:
        logger.info("Language STT unavailable — OpenAI not configured and Whisper disabled")
        return ConversationTranscription(text="", raw_text="", engine="disabled", model="")

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        result, elapsed = await asyncio.to_thread(_transcribe_sync, tmp_path)
        # The stricter anti-hallucination gate is placement-specific. Other callers include
        # single-word pronunciation exercises where a two-word minimum would be incorrect.
        if audio_duration_s is not None:
            apply_transcript_evidence_gate(result, audio_duration_s=audio_duration_s)
        logger.info(
            "Conversation transcription engine=%s model=%s latency_s=%.2f audio_duration_s=%.2f "
            "characters=%d low_confidence=%s",
            result.engine,
            result.model,
            elapsed,
            result.duration_s,
            len(result.text),
            result.low_confidence,
        )
        return result
    except AudioDecoderTimeout:
        logger.warning("English transcription failed code=decoder_timeout")
        return ConversationTranscription(
            text="", raw_text="", engine="error", model="", meta={"error_code": "decoder_timeout"}
        )
    except InvalidAudio:
        logger.warning("English transcription failed code=invalid_audio")
        return ConversationTranscription(
            text="", raw_text="", engine="error", model="", meta={"error_code": "invalid_audio"}
        )
    except Exception as exc:
        logger.warning("English transcription failed error_type=%s", type(exc).__name__)
        return ConversationTranscription(
            text="", raw_text="", engine="error", model="", meta={"error_code": "stt_unavailable"}
        )
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
