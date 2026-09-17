"""Map existing MediaObject storage into canonical SpeakingAudioArtifact (S4)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import get_settings
from app.models.media import MediaObject, StorageProvider
from app.services.language_speaking.enums import SpeakingAudioSource
from app.services.language_speaking_audio_frontend.artifacts import (
    AudioIntegrityMetadata,
    ClientRecordingMetadata,
    SpeakingAudioArtifact,
)
from app.services.language_speaking_audio_frontend.errors import AudioNotFoundError

settings = get_settings()

_MIME_TO_CODEC: dict[str, str] = {
    "audio/webm": "opus",
    "audio/wav": "pcm_s16le",
    "audio/x-wav": "pcm_s16le",
    "audio/mpeg": "mp3",
    "audio/ogg": "ogg",
    "audio/opus": "opus",
    "audio/mp4": "aac",
    "audio/flac": "flac",
}

_MIME_TO_CONTAINER: dict[str, str] = {
    "audio/webm": "webm",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
    "audio/ogg": "ogg",
    "audio/opus": "opus",
    "audio/mp4": "m4a",
    "audio/flac": "flac",
}


def read_media_bytes(media: MediaObject) -> bytes:
    """Read audio bytes from local storage. Raises AudioNotFoundError on failure."""
    if media.storage_provider != StorageProvider.local.value:
        raise AudioNotFoundError(
            "Non-local storage not supported in S4 runtime",
            detail=str(media.storage_provider),
        )
    if not media.storage_key:
        raise AudioNotFoundError("MediaObject has no storage_key")
    path = Path(settings.UPLOAD_DIR) / media.storage_key
    if not path.is_file():
        raise AudioNotFoundError("Audio file not found on disk", detail=str(path))
    return path.read_bytes()


def artifact_from_media_object(
    media: MediaObject,
    *,
    session_id: str,
    student_id: int,
    language_id: int,
    audio_source: SpeakingAudioSource = SpeakingAudioSource.browser_recording,
    captured_at: datetime | None = None,
    audio_bytes: bytes | None = None,
) -> SpeakingAudioArtifact:
    """Build SpeakingAudioArtifact from MediaObject. Unknown metadata stays explicit."""
    content_type = (media.mime_type or "").strip()
    filename = media.original_filename or "recording.webm"
    suffix = Path(filename).suffix.lower()
    container = _MIME_TO_CONTAINER.get(content_type, suffix.lstrip(".") or "unknown")
    codec = _MIME_TO_CODEC.get(content_type, "unknown")

    storage_ref = media.public_url or f"/uploads/{media.storage_key}"
    byte_size = int(media.file_size_bytes or 0)

    integrity = AudioIntegrityMetadata()
    if audio_bytes is None:
        try:
            audio_bytes = read_media_bytes(media)
            byte_size = len(audio_bytes)
        except AudioNotFoundError:
            audio_bytes = None

    if audio_bytes:
        digest = hashlib.sha256(audio_bytes).hexdigest()
        integrity = AudioIntegrityMetadata(content_hash=digest, hash_algorithm="sha256", verified=True)
        if not byte_size:
            byte_size = len(audio_bytes)

    return SpeakingAudioArtifact(
        audio_id=f"media_{media.id}",
        session_id=session_id,
        student_id=student_id,
        language_id=language_id,
        source_type=audio_source,
        original_filename=filename,
        content_type=content_type or "audio/webm",
        codec=codec,
        container_format=container,
        sample_rate_hz=0,
        channel_count=0,
        duration_ms=0,
        byte_size=byte_size,
        storage_reference=storage_ref,
        captured_at=captured_at or datetime.now(tz=timezone.utc),
        client_recording_metadata=ClientRecordingMetadata(mime_type=content_type),
        integrity=integrity,
    )


def artifact_from_bytes(
    *,
    audio_id: str,
    session_id: str,
    student_id: int,
    language_id: int,
    audio_bytes: bytes,
    original_filename: str,
    content_type: str,
    audio_source: SpeakingAudioSource = SpeakingAudioSource.file_upload,
    storage_reference: str = "",
    captured_at: datetime | None = None,
) -> SpeakingAudioArtifact:
    """Build SpeakingAudioArtifact directly from in-memory bytes (tests / direct upload)."""
    suffix = Path(original_filename).suffix.lower()
    container = _MIME_TO_CONTAINER.get(content_type, suffix.lstrip(".") or "unknown")
    codec = _MIME_TO_CODEC.get(content_type, "unknown")
    digest = hashlib.sha256(audio_bytes).hexdigest() if audio_bytes else ""

    return SpeakingAudioArtifact(
        audio_id=audio_id,
        session_id=session_id,
        student_id=student_id,
        language_id=language_id,
        source_type=audio_source,
        original_filename=original_filename,
        content_type=content_type,
        codec=codec,
        container_format=container,
        sample_rate_hz=0,
        channel_count=0,
        duration_ms=0,
        byte_size=len(audio_bytes),
        storage_reference=storage_reference or f"memory://{audio_id}",
        captured_at=captured_at or datetime.now(tz=timezone.utc),
        client_recording_metadata=ClientRecordingMetadata(mime_type=content_type),
        integrity=AudioIntegrityMetadata(
            content_hash=digest,
            hash_algorithm="sha256",
            verified=bool(digest),
        ),
    )
