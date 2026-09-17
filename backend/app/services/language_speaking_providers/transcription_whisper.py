"""Faster-whisper SpeechTranscriptionProvider (S4 real implementation)."""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

from app.core.config import get_settings
from app.services.language_speaking_providers.capabilities import TranscriptionCapabilities
from app.services.language_speaking_providers.providers import SpeechTranscriptionProvider
from app.services.model_cache import configure_model_cache

logger = logging.getLogger(__name__)
settings = get_settings()

_whisper_model = None

DEFAULT_INITIAL_PROMPT = (
    "English speaking practice. The student introduces themselves. "
    "My name is Hamza. My name are Hamza Al-Kuzbari."
)


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    configure_model_cache()
    from faster_whisper import WhisperModel

    model_id = (settings.LANGUAGE_CONVERSATION_WHISPER_MODEL or "small.en").strip()
    compute = (settings.LANGUAGE_CONVERSATION_WHISPER_COMPUTE_TYPE or "float32").strip()
    logger.info(
        "Loading S4 faster-whisper model=%s compute_type=%s device=cpu",
        model_id,
        compute,
    )
    _whisper_model = WhisperModel(model_id, device="cpu", compute_type=compute)
    return _whisper_model


def _transcribe_sync(
    wav_path: Path,
    *,
    language: str,
    initial_prompt: str,
) -> dict[str, object]:
    model = _get_whisper_model()
    model_id = (settings.LANGUAGE_CONVERSATION_WHISPER_MODEL or "small.en").strip()
    beam = max(1, int(settings.LANGUAGE_CONVERSATION_WHISPER_BEAM_SIZE or 5))
    vad = bool(settings.LANGUAGE_CONVERSATION_WHISPER_VAD)
    prompt = initial_prompt or (settings.LANGUAGE_CONVERSATION_WHISPER_INITIAL_PROMPT or DEFAULT_INITIAL_PROMPT)

    segments_iter, info = model.transcribe(
        str(wav_path),
        language=language,
        beam_size=beam,
        best_of=beam,
        vad_filter=vad,
        initial_prompt=prompt or None,
        condition_on_previous_text=False,
        word_timestamps=True,
    )
    seg_list = list(segments_iter)

    segments: list[dict[str, object]] = []
    words: list[dict[str, object]] = []
    logprobs: list[float] = []
    no_speech_probs: list[float] = []

    for seg in seg_list:
        if seg.avg_logprob is not None:
            logprobs.append(float(seg.avg_logprob))
        if seg.no_speech_prob is not None:
            no_speech_probs.append(float(seg.no_speech_prob))
        segments.append(
            {
                "text": (seg.text or "").strip(),
                "start_sec": float(seg.start),
                "end_sec": float(seg.end),
                "confidence": float(seg.avg_logprob) if seg.avg_logprob is not None else 0.0,
            }
        )
        if seg.words:
            for w in seg.words:
                words.append(
                    {
                        "word": (w.word or "").strip(),
                        "start_sec": float(w.start),
                        "end_sec": float(w.end),
                        "confidence": float(w.probability) if w.probability is not None else 0.0,
                    }
                )

    text = "".join(s.text for s in seg_list).strip()
    avg_logprob = sum(logprobs) / len(logprobs) if logprobs else None
    provider_confidence = 0.0
    if avg_logprob is not None:
        # Map logprob to 0-1-ish confidence for canonical evidence (heuristic).
        provider_confidence = max(0.0, min(1.0, 1.0 + avg_logprob))

    return {
        "text": text,
        "language": getattr(info, "language", None) or language,
        "provider_confidence": provider_confidence,
        "segments": segments,
        "words": words,
        "duration_s": float(getattr(info, "duration", 0.0) or 0.0),
        "language_probability": float(getattr(info, "language_probability", 0.0) or 0.0),
        "avg_logprob": avg_logprob,
        "no_speech_prob": max(no_speech_probs) if no_speech_probs else None,
        "model": model_id,
        "provider_name": "faster_whisper",
        "provider_version": "faster-whisper",
        "processing_version": "s4_whisper",
        "segment_count": len(segments),
    }


class FasterWhisperTranscriptionProvider(SpeechTranscriptionProvider):
    """Real offline transcription via faster-whisper with word timestamps."""

    def capabilities(self) -> TranscriptionCapabilities:
        return TranscriptionCapabilities(
            supports_word_timestamps=True,
            supports_confidence_scores=True,
            supports_streaming=False,
            supported_languages=("en",),
            provider_name="faster_whisper",
        )

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
        language: str = "en",
        initial_prompt: str = "",
    ) -> dict[str, object]:
        if not audio_bytes:
            return {
                "text": "",
                "language": language,
                "provider_confidence": 0.0,
                "segments": [],
                "words": [],
                "model": (settings.LANGUAGE_CONVERSATION_WHISPER_MODEL or "small.en").strip(),
                "provider_name": "faster_whisper",
            }

        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_bytes)
                tmp_path = Path(tmp.name)
            timeout = max(1, int(settings.SPEAKING_TRANSCRIPTION_TIMEOUT_SECONDS or 120))
            return await asyncio.wait_for(
                asyncio.to_thread(
                    _transcribe_sync,
                    tmp_path,
                    language=language,
                    initial_prompt=initial_prompt,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError as exc:
            raise TimeoutError("faster-whisper transcription timed out") from exc
        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
