"""Pronunciation runtime — provider dict to S3 PhonemeAlignmentEvidence (S5)."""

from __future__ import annotations

import asyncio
from datetime import datetime

from app.core.config import get_settings
from app.services.language_speaking_audio_frontend.enums import (
    AudioEvidenceQualityFlag,
    SpeakingEvidenceFamily,
)
from app.services.language_speaking_audio_frontend.errors import (
    PronunciationAlignmentFailedError,
    PronunciationAnalysisFailedError,
    PronunciationAudioMissingError,
    PronunciationEvidenceEmptyError,
    PronunciationEvidenceUnreliableError,
    PronunciationReferenceMissingError,
    PronunciationTimeoutError,
)
from app.services.language_speaking_audio_frontend.evidence import (
    PhonemeAlignmentEntry,
    PhonemeAlignmentEvidence,
    ProviderProvenance,
)
from app.services.language_speaking_audio_frontend.pronunciation_factory import build_pronunciation_provider
from app.services.language_speaking_providers.providers import PhonemeAlignmentProvider

settings = get_settings()


def provider_dict_to_phoneme_alignment_evidence(
    raw: dict[str, object],
    *,
    generated_at: datetime | None = None,
) -> tuple[PhonemeAlignmentEvidence, tuple[AudioEvidenceQualityFlag, ...]]:
    """Convert provider-native dict to canonical S3 PhonemeAlignmentEvidence."""
    alignments: list[PhonemeAlignmentEntry] = []
    for i, item in enumerate(list(raw.get("phoneme_observations") or [])):
        if not isinstance(item, dict):
            continue
        exp = str(item.get("expected_phoneme") or "")
        obs = str(item.get("observed_phoneme") or "")
        if not exp and not obs:
            continue
        alignments.append(
            PhonemeAlignmentEntry(
                expected_phoneme=exp,
                observed_phoneme=obs,
                start_sec=float(item.get("start_sec") or 0.0),
                end_sec=float(item.get("end_sec") or 0.0),
                alignment_confidence=float(item.get("alignment_confidence") or 0.0),
                word_reference=str(item.get("word_reference") or ""),
                position=int(item.get("position") or i),
            )
        )

    quality_flags: list[AudioEvidenceQualityFlag] = []
    unavailable = list(raw.get("unavailable_evidence") or [])
    if not alignments:
        quality_flags.append(AudioEvidenceQualityFlag.alignment_unavailable)
    if "evidence_unreliable" in unavailable or "audio_too_short" in unavailable:
        quality_flags.append(AudioEvidenceQualityFlag.low_audio_quality)

    provenance = ProviderProvenance(
        provider_name=str(raw.get("provider_name") or "unknown"),
        model_name=str(raw.get("model") or ""),
        provider_version=str(raw.get("provider_version") or ""),
        processing_version=str(raw.get("processing_version") or "s5"),
        generated_at=generated_at,
        evidence_family=SpeakingEvidenceFamily.phoneme_alignment,
    )

    evidence = PhonemeAlignmentEvidence(
        alignments=tuple(alignments),
        provenance=provenance,
    )
    return evidence, tuple(quality_flags)


async def analyze_pronunciation_audio(
    wav_bytes: bytes,
    *,
    reference_text: str,
    transcript: str = "",
    provider: PhonemeAlignmentProvider | None = None,
    provider_name: str | None = None,
    generated_at: datetime | None = None,
) -> tuple[dict[str, object], PhonemeAlignmentEvidence, tuple[AudioEvidenceQualityFlag, ...], PhonemeAlignmentProvider]:
    """Run pronunciation analysis on normalized WAV bytes."""
    if not wav_bytes:
        raise PronunciationAudioMissingError("Normalized audio bytes are missing")

    ref = (reference_text or transcript or "").strip()
    if not ref:
        raise PronunciationReferenceMissingError("Pronunciation reference text is missing")

    prov = provider or build_pronunciation_provider(provider_name)
    timeout = max(1, int(settings.SPEAKING_PRONUNCIATION_TIMEOUT_SECONDS or 120))
    try:
        raw = await asyncio.wait_for(
            prov.align(
                audio_bytes=wav_bytes,
                transcript=transcript,
                reference_text=reference_text,
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError as exc:
        raise PronunciationTimeoutError("Pronunciation analysis timed out") from exc
    except (
        PronunciationAudioMissingError,
        PronunciationReferenceMissingError,
        PronunciationTimeoutError,
    ):
        raise
    except Exception as exc:
        raise PronunciationAnalysisFailedError(
            "Pronunciation analysis failed",
            detail=type(exc).__name__,
        ) from exc

    if not isinstance(raw, dict):
        raise PronunciationAnalysisFailedError("Provider returned non-dict response")

    unavailable = list(raw.get("unavailable_evidence") or [])
    if "reference_missing" in unavailable:
        raise PronunciationReferenceMissingError("Provider reported missing reference")
    if "audio_missing" in unavailable:
        raise PronunciationAudioMissingError("Provider reported missing audio")

    try:
        evidence, flags = provider_dict_to_phoneme_alignment_evidence(raw, generated_at=generated_at)
    except Exception as exc:
        raise PronunciationAlignmentFailedError(
            "Failed to map phoneme alignment evidence",
            detail=type(exc).__name__,
        ) from exc

    if not evidence.alignments and "phoneme_decode_empty" in unavailable:
        raise PronunciationEvidenceEmptyError("Pronunciation evidence is empty")

    if "evidence_unreliable" in unavailable and not evidence.alignments:
        raise PronunciationEvidenceUnreliableError("Pronunciation evidence is unreliable")

    return raw, evidence, flags, prov
