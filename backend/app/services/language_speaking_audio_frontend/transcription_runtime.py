"""Transcription runtime — provider dict to canonical TranscriptEvidence (S4)."""

from __future__ import annotations

import asyncio
from datetime import datetime

from app.core.config import get_settings
from app.services.language_speaking.types import WordTiming
from app.services.language_speaking_audio_frontend.enums import (
    AudioEvidenceQualityFlag,
    SpeakingEvidenceFamily,
)
from app.services.language_speaking_audio_frontend.errors import (
    EmptyTranscriptError,
    TranscriptionFailedError,
    TranscriptionTimeoutError,
)
from app.services.language_speaking_audio_frontend.evidence import (
    ProviderProvenance,
    TranscriptEvidence,
    TranscriptSegment,
)
from app.services.language_speaking_audio_frontend.transcription_factory import build_transcription_provider
from app.services.language_speaking_providers.providers import SpeechTranscriptionProvider

settings = get_settings()


def _map_segments(raw_segments: list[object]) -> tuple[TranscriptSegment, ...]:
    out: list[TranscriptSegment] = []
    for item in raw_segments:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        out.append(
            TranscriptSegment(
                text=text,
                start_sec=float(item.get("start_sec", 0.0)),
                end_sec=float(item.get("end_sec", 0.0)),
                confidence=float(item.get("confidence", 0.0)),
            )
        )
    return tuple(out)


def _map_words(raw_words: list[object]) -> tuple[WordTiming, ...]:
    out: list[WordTiming] = []
    for item in raw_words:
        if not isinstance(item, dict):
            continue
        word = str(item.get("word") or "").strip()
        if not word:
            continue
        out.append(
            WordTiming(
                word=word,
                start_sec=float(item.get("start_sec", 0.0)),
                end_sec=float(item.get("end_sec", 0.0)),
                confidence=float(item.get("confidence", 0.0)),
            )
        )
    return tuple(out)


def provider_dict_to_transcript_evidence(
    raw: dict[str, object],
    *,
    generated_at: datetime | None = None,
) -> tuple[TranscriptEvidence, tuple[AudioEvidenceQualityFlag, ...]]:
    """Convert provider-native dict to canonical TranscriptEvidence."""
    text = str(raw.get("text") or "").strip()
    if not text:
        raise EmptyTranscriptError("Transcription returned empty text")

    language = str(raw.get("language") or "en")
    # Confidence may be genuinely unavailable (e.g. OpenAI gpt-4o json). Distinguish
    # "unknown" from a real low score so we never fabricate a quality judgement.
    confidence_raw = raw.get("provider_confidence")
    confidence_available = confidence_raw is not None
    confidence = float(confidence_raw) if confidence_available else 0.0
    segments = _map_segments(list(raw.get("segments") or []))
    words = _map_words(list(raw.get("words") or []))

    quality_flags: list[AudioEvidenceQualityFlag] = []
    if not words:
        quality_flags.append(AudioEvidenceQualityFlag.timestamp_unavailable)
    if confidence_available and confidence < 0.3:
        quality_flags.append(AudioEvidenceQualityFlag.low_audio_quality)

    provenance = ProviderProvenance(
        provider_name=str(raw.get("provider_name") or "unknown"),
        model_name=str(raw.get("model") or ""),
        provider_version=str(raw.get("provider_version") or ""),
        processing_version=str(raw.get("processing_version") or "s4"),
        generated_at=generated_at,
        evidence_family=SpeakingEvidenceFamily.transcript,
    )

    evidence = TranscriptEvidence(
        text=text,
        language=language,
        provider_confidence=confidence,
        segments=segments,
        words=words,
        provenance=provenance,
    )
    return evidence, tuple(quality_flags)


async def transcribe_normalized_audio(
    wav_bytes: bytes,
    *,
    provider: SpeechTranscriptionProvider | None = None,
    provider_name: str | None = None,
    language: str = "en",
    initial_prompt: str = "",
    generated_at: datetime | None = None,
) -> tuple[TranscriptEvidence, tuple[AudioEvidenceQualityFlag, ...], SpeechTranscriptionProvider]:
    """Run transcription on normalized WAV bytes and return canonical evidence."""
    prov = provider or build_transcription_provider(provider_name)
    timeout = max(1, int(settings.SPEAKING_TRANSCRIPTION_TIMEOUT_SECONDS or 120))
    try:
        raw = await asyncio.wait_for(
            prov.transcribe(
                audio_bytes=wav_bytes,
                mime_type="audio/wav",
                language=language,
                initial_prompt=initial_prompt,
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError as exc:
        raise TranscriptionTimeoutError("Transcription timed out") from exc
    except EmptyTranscriptError:
        raise
    except Exception as exc:
        raise TranscriptionFailedError("Transcription failed", detail=type(exc).__name__) from exc

    if not isinstance(raw, dict):
        raise TranscriptionFailedError("Provider returned non-dict response")

    try:
        evidence, flags = provider_dict_to_transcript_evidence(raw, generated_at=generated_at)
    except EmptyTranscriptError:
        raise
    except Exception as exc:
        raise TranscriptionFailedError("Failed to map transcript evidence", detail=type(exc).__name__) from exc

    return evidence, flags, prov
