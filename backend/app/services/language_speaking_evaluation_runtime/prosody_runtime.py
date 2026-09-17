"""S6 prosody analysis orchestrator."""

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
    ProsodyAnalysisFailedError,
    ProsodyAudioMissingError,
    ProsodyAuthenticationFailedError,
    ProsodyEvidenceEmptyError,
    ProsodyEvidenceUnreliableError,
    ProsodyProviderDiscontinuedError,
    ProsodyProviderUnavailableError,
    ProsodyRateLimitedError,
    ProsodyResponseInvalidError,
    ProsodyTimeoutError,
    SpeakingAudioRuntimeError,
)
from app.services.language_speaking_audio_frontend.normalization_runtime import normalize_audio_with_bytes
from app.services.language_speaking_audio_frontend.prosody_runtime import analyze_prosody_audio
from app.services.language_speaking_prosody.assembler import assemble_prosody_evidence
from app.services.language_speaking_prosody.types import SpeakingProsodyEvidenceResult


@dataclass(frozen=True, slots=True)
class SpeakingProsodyRuntimeResult:
    """Result of process_speaking_prosody — prosody facts only."""

    success: bool
    prosody: SpeakingProsodyEvidenceResult | None = None
    bundle: SpeakingAudioEvidenceBundle | None = None
    raw_artifact: SpeakingAudioArtifact | None = None
    normalized_artifact: NormalizedAudioArtifact | None = None
    error: SpeakingAudioRuntimeError | None = None
    processing_warnings: tuple[str, ...] = field(default_factory=tuple)


async def process_speaking_prosody(
    artifact: SpeakingAudioArtifact,
    audio_bytes: bytes,
    *,
    existing_bundle: SpeakingAudioEvidenceBundle | None = None,
    provider_name: str | None = None,
    now: datetime | None = None,
) -> SpeakingProsodyRuntimeResult:
    """Canonical S6 entry: normalize audio -> prosody evidence -> evidence bundle."""
    ts = now or datetime.now(tz=timezone.utc)
    warnings: list[str] = []

    try:
        normalized, wav_bytes, norm_warnings = normalize_audio_with_bytes(artifact, audio_bytes, now=ts)
        warnings.extend(norm_warnings)

        raw_dict, prosody_evidence, pros_flags, _prov = await analyze_prosody_audio(
            wav_bytes,
            provider_name=provider_name,
            generated_at=ts,
        )
        warnings.extend(f.value for f in pros_flags)
        warnings.extend(str(w) for w in (raw_dict.get("processing_warnings") or []))

        prosody = assemble_prosody_evidence(
            raw_dict,
            audio_id=artifact.audio_id,
            session_id=artifact.session_id,
            source_audio_id=artifact.audio_id,
        )

        all_quality_flags: list[AudioEvidenceQualityFlag] = list(pros_flags)
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
            phoneme_alignment=existing_bundle.phoneme_alignment if existing_bundle else None,
            prosody=prosody_evidence,
            processing_warnings=tuple(dict.fromkeys(warnings)),
            quality_flags=tuple(dict.fromkeys(all_quality_flags)),
            assembled_at=ts,
        )

        return SpeakingProsodyRuntimeResult(
            success=True,
            prosody=prosody,
            bundle=bundle,
            raw_artifact=artifact,
            normalized_artifact=normalized,
            processing_warnings=tuple(dict.fromkeys(warnings)),
        )

    except SpeakingAudioRuntimeError as exc:
        return SpeakingProsodyRuntimeResult(
            success=False,
            raw_artifact=artifact,
            error=exc,
            processing_warnings=tuple(warnings),
        )
    except Exception as exc:
        wrapped = ProsodyAnalysisFailedError("Unexpected prosody runtime failure", detail=type(exc).__name__)
        return SpeakingProsodyRuntimeResult(
            success=False,
            raw_artifact=artifact,
            error=wrapped,
            processing_warnings=tuple(warnings),
        )


__all__ = [
    "NormalizationFailedError",
    "ProsodyAnalysisFailedError",
    "ProsodyAudioMissingError",
    "ProsodyAuthenticationFailedError",
    "ProsodyEvidenceEmptyError",
    "ProsodyEvidenceUnreliableError",
    "ProsodyProviderDiscontinuedError",
    "ProsodyProviderUnavailableError",
    "ProsodyRateLimitedError",
    "ProsodyResponseInvalidError",
    "ProsodyTimeoutError",
    "SpeakingProsodyRuntimeResult",
    "process_speaking_prosody",
]
