"""S4 audio ingestion + transcription orchestrator."""

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
    EmptyTranscriptError,
    EvidenceBundleAssemblyFailedError,
    NormalizationFailedError,
    NormalizedAudioInvalidError,
    SessionTransitionError,
    SpeakingAudioRuntimeError,
    TranscriptionFailedError,
    TranscriptionProviderUnavailableError,
    TranscriptionTimeoutError,
    UnsupportedAudioFormatError,
)
from app.services.language_speaking_audio_frontend.normalization_runtime import normalize_audio_with_bytes
from app.services.language_speaking_audio_frontend.transcription_runtime import transcribe_normalized_audio
from app.services.language_speaking_audio_session.enums import SpeakingAudioLifecycleState
from app.services.language_speaking_audio_session.transitions import is_legal_transition
from app.services.language_speaking_audio_session.types import SpeakingAudioSessionRecord

LANGUAGE_SPEAKING_EVALUATION_RUNTIME_VERSION = "0.4.0"


@dataclass(frozen=True, slots=True)
class SpeakingAudioRuntimeResult:
    """Result of process_speaking_audio — evidence only, no educational scoring."""

    success: bool
    session: SpeakingAudioSessionRecord
    raw_artifact: SpeakingAudioArtifact
    normalized_artifact: NormalizedAudioArtifact | None = None
    bundle: SpeakingAudioEvidenceBundle | None = None
    error: SpeakingAudioRuntimeError | None = None
    processing_warnings: tuple[str, ...] = field(default_factory=tuple)


def _advance_session(
    session: SpeakingAudioSessionRecord,
    to_state: SpeakingAudioLifecycleState,
    *,
    now: datetime,
    failure_reason: str = "",
) -> SpeakingAudioSessionRecord:
    if not is_legal_transition(session.lifecycle_state, to_state):
        raise SessionTransitionError(
            f"Illegal transition {session.lifecycle_state.value} -> {to_state.value}",
        )
    return session.with_transition(to_state, now=now, failure_reason=failure_reason)


def _fail_session(
    session: SpeakingAudioSessionRecord,
    *,
    now: datetime,
    reason: str,
) -> SpeakingAudioSessionRecord:
    if is_legal_transition(session.lifecycle_state, SpeakingAudioLifecycleState.failed):
        return session.with_transition(
            SpeakingAudioLifecycleState.failed,
            now=now,
            failure_reason=reason,
        )
    if is_legal_transition(session.lifecycle_state, SpeakingAudioLifecycleState.expired):
        return session.with_transition(SpeakingAudioLifecycleState.expired, now=now, failure_reason=reason)
    return session


async def process_speaking_audio(
    artifact: SpeakingAudioArtifact,
    audio_bytes: bytes,
    *,
    session: SpeakingAudioSessionRecord | None = None,
    provider_name: str | None = None,
    language: str = "en",
    initial_prompt: str = "",
    now: datetime | None = None,
) -> SpeakingAudioRuntimeResult:
    """Canonical S4 entry: artifact -> normalize -> transcribe -> evidence bundle."""
    ts = now or datetime.now(tz=timezone.utc)
    warnings: list[str] = []

    if session is None:
        session = SpeakingAudioSessionRecord(
            session_id=artifact.session_id,
            student_id=artifact.student_id,
            language_id=artifact.language_id,
            audio_source=artifact.source_type,
            lifecycle_state=SpeakingAudioLifecycleState.created,
            audio_id=artifact.audio_id,
            created_at=ts,
            updated_at=ts,
        )

    try:
        session = _advance_session(session, SpeakingAudioLifecycleState.uploading, now=ts)
        session = _advance_session(session, SpeakingAudioLifecycleState.uploaded, now=ts)
        session = _advance_session(session, SpeakingAudioLifecycleState.normalizing, now=ts)

        normalized, wav_bytes, norm_warnings = normalize_audio_with_bytes(artifact, audio_bytes, now=ts)
        warnings.extend(norm_warnings)

        session = _advance_session(session, SpeakingAudioLifecycleState.ready, now=ts)
        session = _advance_session(session, SpeakingAudioLifecycleState.processing, now=ts)

        transcript, tx_flags, _prov = await transcribe_normalized_audio(
            wav_bytes,
            provider_name=provider_name,
            language=language,
            initial_prompt=initial_prompt,
            generated_at=ts,
        )
        warnings.extend(flag.value for flag in tx_flags)

        bundle_id = f"bundle_{artifact.audio_id}_{uuid.uuid4().hex[:8]}"
        try:
            bundle = assemble_evidence_bundle(
                evidence_bundle_id=bundle_id,
                session_id=artifact.session_id,
                audio_id=artifact.audio_id,
                transcript=transcript,
                speech_embedding=None,
                phoneme_alignment=None,
                prosody=None,
                processing_warnings=tuple(warnings),
                quality_flags=tx_flags,
                assembled_at=ts,
            )
        except Exception as exc:
            raise EvidenceBundleAssemblyFailedError(
                "Failed to assemble evidence bundle",
                detail=type(exc).__name__,
            ) from exc

        session = _advance_session(session, SpeakingAudioLifecycleState.processed, now=ts)

        return SpeakingAudioRuntimeResult(
            success=True,
            session=session,
            raw_artifact=artifact,
            normalized_artifact=normalized,
            bundle=bundle,
            processing_warnings=tuple(warnings),
        )

    except SpeakingAudioRuntimeError as exc:
        failed_session = _fail_session(session, now=ts, reason=exc.code)
        return SpeakingAudioRuntimeResult(
            success=False,
            session=failed_session,
            raw_artifact=artifact,
            error=exc,
            processing_warnings=tuple(warnings),
        )
    except Exception as exc:
        failed_session = _fail_session(session, now=ts, reason="speaking_audio_runtime_error")
        wrapped = TranscriptionFailedError("Unexpected runtime failure", detail=type(exc).__name__)
        return SpeakingAudioRuntimeResult(
            success=False,
            session=failed_session,
            raw_artifact=artifact,
            error=wrapped,
            processing_warnings=tuple(warnings),
        )


__all__ = [
    "EmptyTranscriptError",
    "EvidenceBundleAssemblyFailedError",
    "LANGUAGE_SPEAKING_EVALUATION_RUNTIME_VERSION",
    "NormalizationFailedError",
    "NormalizedAudioInvalidError",
    "SessionTransitionError",
    "SpeakingAudioRuntimeResult",
    "TranscriptionFailedError",
    "TranscriptionProviderUnavailableError",
    "TranscriptionTimeoutError",
    "UnsupportedAudioFormatError",
    "process_speaking_audio",
]
