"""Canonical audio input and normalization contracts (S3).

Raw audio bytes are never stored inside canonical educational result objects.
Only storage references and metadata travel downstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.services.language_speaking.enums import SpeakingAudioSource
from app.services.language_speaking_audio_frontend.enums import AudioArtifactKind

LANGUAGE_SPEAKING_AUDIO_FRONTEND_VERSION = "0.3.0"

# Future normalization target — contract only, no ffmpeg processing in S3.
CANONICAL_SAMPLE_RATE_HZ = 16_000
CANONICAL_CHANNEL_COUNT = 1
CANONICAL_CONTAINER_FORMAT = "wav"
CANONICAL_CODEC = "pcm_s16le"


@dataclass(frozen=True, slots=True)
class ClientRecordingMetadata:
    """Opaque client-side capture metadata (browser recorder, device hints)."""

    mime_type: str = ""
    recorder_name: str = ""
    device_label: str = ""
    client_timestamp: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AudioIntegrityMetadata:
    """Hash / integrity metadata for traceability — no raw bytes."""

    content_hash: str = ""
    hash_algorithm: str = "sha256"
    verified: bool = False


@dataclass(frozen=True, slots=True)
class SpeakingAudioArtifact:
    """Canonical raw audio artifact — the first-class input to the audio frontend.

    Represents one captured/uploaded audio clip. Raw bytes live at
    ``storage_reference`` only; they are never embedded in educational objects.
    """

    audio_id: str
    session_id: str
    student_id: int
    language_id: int
    source_type: SpeakingAudioSource
    original_filename: str
    content_type: str
    codec: str
    container_format: str
    sample_rate_hz: int
    channel_count: int
    duration_ms: int
    byte_size: int
    storage_reference: str
    captured_at: datetime
    artifact_kind: AudioArtifactKind = AudioArtifactKind.raw
    client_recording_metadata: ClientRecordingMetadata = field(default_factory=ClientRecordingMetadata)
    integrity: AudioIntegrityMetadata = field(default_factory=AudioIntegrityMetadata)
    artifact_version: str = LANGUAGE_SPEAKING_AUDIO_FRONTEND_VERSION

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "audio_id": self.audio_id,
            "session_id": self.session_id,
            "student_id": self.student_id,
            "language_id": self.language_id,
            "source_type": self.source_type.value,
            "original_filename": self.original_filename,
            "content_type": self.content_type,
            "codec": self.codec,
            "container_format": self.container_format,
            "sample_rate_hz": self.sample_rate_hz,
            "channel_count": self.channel_count,
            "duration_ms": self.duration_ms,
            "byte_size": self.byte_size,
            "storage_reference": self.storage_reference,
            "captured_at": self.captured_at.isoformat(),
            "artifact_kind": self.artifact_kind.value,
            "client_recording_metadata": {
                "mime_type": self.client_recording_metadata.mime_type,
                "recorder_name": self.client_recording_metadata.recorder_name,
                "device_label": self.client_recording_metadata.device_label,
                "client_timestamp": self.client_recording_metadata.client_timestamp,
            },
            "integrity": {
                "content_hash": self.integrity.content_hash,
                "hash_algorithm": self.integrity.hash_algorithm,
                "verified": self.integrity.verified,
            },
            "artifact_version": self.artifact_version,
        }


# Alias requested by the S3 spec.
SpeakingAudioInput = SpeakingAudioArtifact


@dataclass(frozen=True, slots=True)
class NormalizedAudioArtifact:
    """Provider-neutral normalized audio metadata.

    Distinguishes the normalized derivative from the raw upload. A future
    normalization step (e.g. ffmpeg to mono PCM/WAV at 16 kHz) produces this
    artifact; S3 defines the contract only.

    ``source_audio_id`` provides raw → normalized traceability.
    """

    audio_id: str
    session_id: str
    student_id: int
    language_id: int
    source_audio_id: str
    storage_reference: str
    content_type: str = "audio/wav"
    codec: str = CANONICAL_CODEC
    container_format: str = CANONICAL_CONTAINER_FORMAT
    sample_rate_hz: int = CANONICAL_SAMPLE_RATE_HZ
    channel_count: int = CANONICAL_CHANNEL_COUNT
    duration_ms: int = 0
    byte_size: int = 0
    normalization_warnings: tuple[str, ...] = ()
    normalized_at: datetime | None = None
    artifact_kind: AudioArtifactKind = AudioArtifactKind.normalized
    artifact_version: str = LANGUAGE_SPEAKING_AUDIO_FRONTEND_VERSION

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "audio_id": self.audio_id,
            "session_id": self.session_id,
            "student_id": self.student_id,
            "language_id": self.language_id,
            "source_audio_id": self.source_audio_id,
            "storage_reference": self.storage_reference,
            "content_type": self.content_type,
            "codec": self.codec,
            "container_format": self.container_format,
            "sample_rate_hz": self.sample_rate_hz,
            "channel_count": self.channel_count,
            "duration_ms": self.duration_ms,
            "byte_size": self.byte_size,
            "normalization_warnings": list(self.normalization_warnings),
            "normalized_at": self.normalized_at.isoformat() if self.normalized_at else None,
            "artifact_kind": self.artifact_kind.value,
            "artifact_version": self.artifact_version,
        }
