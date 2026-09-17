"""S5 pronunciation analysis orchestrator."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.services.language_speaking_audio_frontend.artifacts import (
    NormalizedAudioArtifact,
    SpeakingAudioArtifact,
)
from app.services.language_speaking_audio_frontend.bundle import (
    SpeakingAudioEvidenceBundle,
    assemble_evidence_bundle,
)
from app.services.language_speaking_audio_frontend.enums import AudioEvidenceQualityFlag
from app.services.language_speaking_audio_frontend.errors import (
    NormalizationFailedError,
    PronunciationAnalysisFailedError,
    PronunciationAudioMissingError,
    PronunciationEvidenceEmptyError,
    PronunciationEvidenceUnreliableError,
    PronunciationProviderUnavailableError,
    PronunciationReferenceMissingError,
    PronunciationTimeoutError,
    SpeakingAudioRuntimeError,
)
from app.services.language_speaking_audio_frontend.normalization_runtime import normalize_audio_with_bytes
from app.services.language_speaking_audio_frontend.pronunciation_runtime import analyze_pronunciation_audio
from app.services.language_speaking_pronunciation.assembler import assemble_pronunciation_evidence
from app.services.language_speaking_pronunciation.types import (
    PronunciationReferenceSource,
    SpeakingPronunciationEvidenceResult,
)


@dataclass(frozen=True, slots=True)
class SpeakingPronunciationRuntimeResult:
    """Result of process_speaking_pronunciation — pronunciation facts only."""

    success: bool
    pronunciation: SpeakingPronunciationEvidenceResult | None = None
    bundle: SpeakingAudioEvidenceBundle | None = None
    raw_artifact: SpeakingAudioArtifact | None = None
    normalized_artifact: NormalizedAudioArtifact | None = None
    error: SpeakingAudioRuntimeError | None = None
    processing_warnings: tuple[str, ...] = field(default_factory=tuple)


def _resolve_reference(
    *,
    expected_task_text: str,
    transcript_text: str,
) -> tuple[PronunciationReferenceSource, str]:
    task = (expected_task_text or "").strip()
    if task:
        return PronunciationReferenceSource.expected_task_text, task
    hyp = (transcript_text or "").strip()
    if hyp:
        return PronunciationReferenceSource.transcript_hypothesis, hyp
    return PronunciationReferenceSource.transcript_hypothesis, ""


async def process_speaking_pronunciation(
    artifact: SpeakingAudioArtifact,
    audio_bytes: bytes,
    *,
    expected_task_text: str = "",
    transcript_text: str = "",
    existing_bundle: SpeakingAudioEvidenceBundle | None = None,
    provider_name: str | None = None,
    now: datetime | None = None,
) -> SpeakingPronunciationRuntimeResult:
    """Canonical S5 entry: normalize audio -> acoustic pronunciation -> evidence bundle."""
    ts = now or datetime.now(tz=timezone.utc)
    warnings: list[str] = []

    ref_source, ref_text = _resolve_reference(
        expected_task_text=expected_task_text,
        transcript_text=transcript_text,
    )

    try:
        normalized, wav_bytes, norm_warnings = normalize_audio_with_bytes(artifact, audio_bytes, now=ts)
        warnings.extend(norm_warnings)

        raw_dict, phoneme_evidence, pron_flags, _prov = await analyze_pronunciation_audio(
            wav_bytes,
            reference_text=ref_text,
            transcript=transcript_text,
            provider_name=provider_name,
            generated_at=ts,
        )
        warnings.extend(f.value for f in pron_flags)
        warnings.extend(str(w) for w in (raw_dict.get("processing_warnings") or []))

        pronunciation = assemble_pronunciation_evidence(
            raw_dict,
            audio_id=artifact.audio_id,
            session_id=artifact.session_id,
            reference_source=ref_source,
            reference_text=ref_text,
        )

        all_quality_flags: list[AudioEvidenceQualityFlag] = list(pron_flags)
        if existing_bundle:
            all_quality_flags.extend(existing_bundle.quality_flags)
            warnings.extend(existing_bundle.processing_warnings)

        bundle_id = (
            existing_bundle.evidence_bundle_id
            if existing_bundle
            else f"bundle_{artifact.audio_id}_{uuid.uuid4().hex[:8]}"
        )
        bundle = assemble_evidence_bundle(
            evidence_bundle_id=bundle_id,
            session_id=artifact.session_id,
            audio_id=artifact.audio_id,
            transcript=existing_bundle.transcript if existing_bundle else None,
            speech_embedding=existing_bundle.speech_embedding if existing_bundle else None,
            phoneme_alignment=phoneme_evidence,
            prosody=existing_bundle.prosody if existing_bundle else None,
            processing_warnings=tuple(dict.fromkeys(warnings)),
            quality_flags=tuple(dict.fromkeys(all_quality_flags)),
            assembled_at=ts,
        )

        return SpeakingPronunciationRuntimeResult(
            success=True,
            pronunciation=pronunciation,
            bundle=bundle,
            raw_artifact=artifact,
            normalized_artifact=normalized,
            processing_warnings=tuple(dict.fromkeys(warnings)),
        )

    except SpeakingAudioRuntimeError as exc:
        return SpeakingPronunciationRuntimeResult(
            success=False,
            raw_artifact=artifact,
            error=exc,
            processing_warnings=tuple(warnings),
        )
    except Exception as exc:
        wrapped = PronunciationAnalysisFailedError("Unexpected pronunciation runtime failure", detail=type(exc).__name__)
        return SpeakingPronunciationRuntimeResult(
            success=False,
            raw_artifact=artifact,
            error=wrapped,
            processing_warnings=tuple(warnings),
        )


__all__ = [
    "NormalizationFailedError",
    "PronunciationAnalysisFailedError",
    "PronunciationAudioMissingError",
    "PronunciationEvidenceEmptyError",
    "PronunciationEvidenceUnreliableError",
    "PronunciationProviderUnavailableError",
    "PronunciationReferenceMissingError",
    "PronunciationTimeoutError",
    "SpeakingPronunciationRuntimeResult",
    "process_speaking_pronunciation",
]
