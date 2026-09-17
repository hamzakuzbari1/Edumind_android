"""Real audio normalization runtime (S4) — isolated ffmpeg boundary."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import uuid
import wave
from datetime import datetime
from pathlib import Path

from app.services.language_speaking_audio_frontend.artifacts import (
    CANONICAL_CHANNEL_COUNT,
    CANONICAL_CODEC,
    CANONICAL_CONTAINER_FORMAT,
    CANONICAL_SAMPLE_RATE_HZ,
    NormalizedAudioArtifact,
    SpeakingAudioArtifact,
)
from app.services.language_speaking_audio_frontend.errors import (
    NormalizationFailedError,
    NormalizedAudioInvalidError,
    UnsupportedAudioFormatError,
)

_SUPPORTED_INPUT_SUFFIXES = frozenset(
    {".webm", ".wav", ".mp3", ".ogg", ".opus", ".m4a", ".flac", ".aac", ".mp4", ".mkv"}
)


def _resolve_ffmpeg() -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _suffix_from_content_type(content_type: str) -> str:
    mapping = {
        "audio/webm": ".webm",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/ogg": ".ogg",
        "audio/opus": ".opus",
        "audio/mp4": ".m4a",
        "audio/flac": ".flac",
        "video/webm": ".webm",
    }
    return mapping.get((content_type or "").split(";")[0].strip().lower(), ".webm")


def _run_ffmpeg_normalize(source_path: Path, out_path: Path) -> None:
    ffmpeg = _resolve_ffmpeg()
    if not ffmpeg:
        raise NormalizationFailedError("ffmpeg not available for audio normalization")
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(source_path),
        "-ar",
        str(CANONICAL_SAMPLE_RATE_HZ),
        "-ac",
        str(CANONICAL_CHANNEL_COUNT),
        "-c:a",
        "pcm_s16le",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not out_path.exists() or out_path.stat().st_size == 0:
        raise NormalizationFailedError(
            "ffmpeg normalization failed",
            detail=(result.stderr or result.stdout)[-500:],
        )


def _inspect_wav(path: Path) -> tuple[int, int, int, int]:
    """Return (sample_rate_hz, channel_count, duration_ms, byte_size)."""
    with wave.open(str(path), "rb") as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        frames = wf.getnframes()
        sampwidth = wf.getsampwidth()
        duration_ms = int((frames / sample_rate) * 1000) if sample_rate else 0
        byte_size = frames * channels * sampwidth
    file_size = path.stat().st_size
    return sample_rate, channels, duration_ms, file_size


def _input_suffix(artifact: SpeakingAudioArtifact) -> str:
    suffix = Path(artifact.original_filename).suffix.lower() if artifact.original_filename else ""
    if not suffix or suffix not in _SUPPORTED_INPUT_SUFFIXES:
        suffix = _suffix_from_content_type(artifact.content_type)
    return suffix


def normalize_audio_with_bytes(
    artifact: SpeakingAudioArtifact,
    audio_bytes: bytes,
    *,
    normalized_storage_reference: str | None = None,
    now: datetime | None = None,
) -> tuple[NormalizedAudioArtifact, bytes, tuple[str, ...]]:
    """Normalize raw audio to canonical WAV; return artifact, wav bytes, warnings."""
    if not audio_bytes:
        raise UnsupportedAudioFormatError("Audio input is empty", detail="zero_byte_payload")

    suffix = _input_suffix(artifact)
    source_path: Path | None = None
    out_path: Path | None = None
    warnings: list[str] = []

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as src_tmp:
            src_tmp.write(audio_bytes)
            source_path = Path(src_tmp.name)

        fd, out_name = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        out_path = Path(out_name)

        _run_ffmpeg_normalize(source_path, out_path)
        wav_bytes = out_path.read_bytes()
        sample_rate, channels, duration_ms, byte_size = _inspect_wav(out_path)

        if sample_rate != CANONICAL_SAMPLE_RATE_HZ:
            raise NormalizedAudioInvalidError(
                f"normalized sample rate {sample_rate} != {CANONICAL_SAMPLE_RATE_HZ}",
            )
        if channels != CANONICAL_CHANNEL_COUNT:
            raise NormalizedAudioInvalidError(
                f"normalized channel count {channels} != {CANONICAL_CHANNEL_COUNT}",
            )
        if duration_ms <= 0:
            warnings.append("normalized_duration_zero_or_unknown")
        if artifact.sample_rate_hz and artifact.sample_rate_hz != sample_rate:
            warnings.append(
                f"source_sample_rate_{artifact.sample_rate_hz}_normalized_to_{sample_rate}"
            )
        if artifact.channel_count and artifact.channel_count != channels:
            warnings.append(
                f"source_channels_{artifact.channel_count}_normalized_to_{channels}"
            )

        norm_id = f"norm_{artifact.audio_id}_{uuid.uuid4().hex[:8]}"
        storage_ref = normalized_storage_reference or f"/uploads/normalized/{norm_id}.wav"

        normalized = NormalizedAudioArtifact(
            audio_id=norm_id,
            session_id=artifact.session_id,
            student_id=artifact.student_id,
            language_id=artifact.language_id,
            source_audio_id=artifact.audio_id,
            storage_reference=storage_ref,
            content_type="audio/wav",
            codec=CANONICAL_CODEC,
            container_format=CANONICAL_CONTAINER_FORMAT,
            sample_rate_hz=sample_rate,
            channel_count=channels,
            duration_ms=duration_ms,
            byte_size=byte_size,
            normalization_warnings=tuple(warnings),
            normalized_at=now,
        )
        return normalized, wav_bytes, tuple(warnings)
    finally:
        for p in (source_path, out_path):
            if p and p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass


def normalize_audio_artifact(
    artifact: SpeakingAudioArtifact,
    audio_bytes: bytes,
    *,
    normalized_storage_reference: str | None = None,
    now: datetime | None = None,
) -> tuple[NormalizedAudioArtifact, tuple[str, ...]]:
    """Normalize without returning wav bytes (metadata-only path)."""
    normalized, _wav, warnings = normalize_audio_with_bytes(
        artifact,
        audio_bytes,
        normalized_storage_reference=normalized_storage_reference,
        now=now,
    )
    return normalized, warnings
