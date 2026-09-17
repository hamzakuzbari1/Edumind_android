"""Bounded, content-aware validation for placement speaking uploads."""

from __future__ import annotations

import asyncio
import hashlib
import math
import tempfile
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings
from app.services.language_transcription_service import (
    AudioDecoderTimeout,
    AudioDecoderUnavailable,
    InvalidAudio,
    _normalize_to_wav_16k,
)


ACCEPTED_AUDIO_MIME: dict[str, str] = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/aac": ".aac",
    "audio/flac": ".flac",
}

_MIME_FAMILIES: dict[str, set[str]] = {
    "webm": {"audio/webm"},
    "ogg": {"audio/ogg"},
    "wav": {"audio/wav", "audio/x-wav", "audio/wave"},
    "mp3": {"audio/mpeg", "audio/mp3"},
    "mp4": {"audio/mp4", "audio/x-m4a"},
    "aac": {"audio/aac"},
    "flac": {"audio/flac"},
}
MAX_PLACEMENT_AUDIO_SECONDS = 180.0


class AudioInspectionUnavailable(RuntimeError):
    """The server cannot decode audio safely at the moment."""


class NoSpeechDetected(ValueError):
    """Decoded audio has no usable acoustic signal."""


@dataclass(frozen=True)
class ValidatedAudio:
    data: bytes
    mime_type: str
    suffix: str
    sha256: str
    duration_seconds: float


def _sniff_audio_family(data: bytes) -> str | None:
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "wav"
    if data.startswith(b"\x1aE\xdf\xa3"):
        return "webm"
    if data.startswith(b"OggS"):
        return "ogg"
    if data.startswith(b"fLaC"):
        return "flac"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return "mp4"
    if data.startswith(b"ID3") or (
        len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE6) == 0xE2
    ):
        return "mp3"
    if len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xF6) == 0xF0:
        return "aac"
    return None


def _inspect_decoded_audio(source: Path) -> float:
    normalized: Path | None = None
    try:
        normalized = _normalize_to_wav_16k(source)
        with wave.open(str(normalized), "rb") as wav:
            frame_rate = wav.getframerate()
            frame_count = wav.getnframes()
            if frame_rate <= 0 or frame_count <= 0 or wav.getsampwidth() != 2:
                raise ValueError("Audio contains no decodable samples")
            duration = frame_count / float(frame_rate)
            if duration < 0.35:
                raise ValueError("Audio recording is too short")
            if duration > MAX_PLACEMENT_AUDIO_SECONDS:
                raise ValueError("Audio recording is too long")

            square_sum = 0
            sample_count = 0
            while True:
                chunk = wav.readframes(16_000)
                if not chunk:
                    break
                samples = array("h")
                samples.frombytes(chunk)
                square_sum += sum(int(sample) * int(sample) for sample in samples)
                sample_count += len(samples)
            rms = math.sqrt(square_sum / sample_count) if sample_count else 0.0
            if rms < 45.0:
                raise NoSpeechDetected("Audio recording contains no detectable speech signal")
            return duration
    except (AudioDecoderTimeout, AudioDecoderUnavailable):
        raise
    except InvalidAudio as exc:
        raise ValueError("Audio file is corrupt or cannot be decoded") from exc
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Audio file is corrupt or cannot be decoded") from exc
    finally:
        if normalized:
            normalized.unlink(missing_ok=True)


async def validate_placement_audio(upload: UploadFile) -> ValidatedAudio:
    """Read at most max+1 bytes, verify content type, decode it, and reject silence."""
    declared = (upload.content_type or "").split(";", 1)[0].strip().lower()
    if declared not in ACCEPTED_AUDIO_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"code": "unsupported_audio_type", "message": "Unsupported audio format."},
        )

    max_bytes = max(1, int(get_settings().GENAI_EXAM_MAX_AUDIO_MB)) * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    try:
        while True:
            chunk = await upload.read(min(64 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail={
                        "code": "audio_too_large",
                        "message": f"Audio must be {get_settings().GENAI_EXAM_MAX_AUDIO_MB} MB or smaller.",
                    },
                )
    finally:
        await upload.close()

    data = b"".join(chunks)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "empty_audio", "message": "Audio recording is empty."},
        )

    family = _sniff_audio_family(data[:64])
    if not family or declared not in _MIME_FAMILIES[family]:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "code": "audio_type_mismatch",
                "message": "The uploaded content does not match its declared audio type.",
            },
        )

    suffix = ACCEPTED_AUDIO_MIME[declared]
    source: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            source = Path(tmp.name)
        try:
            duration = await asyncio.to_thread(_inspect_decoded_audio, source)
        except AudioDecoderTimeout as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "decoder_timeout",
                    "message": "Audio decoding timed out. Please retry with a shorter recording.",
                },
            ) from exc
        except AudioDecoderUnavailable as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "audio_validation_unavailable",
                    "message": "Audio validation is temporarily unavailable.",
                },
            ) from exc
        except AudioInspectionUnavailable as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "audio_validation_unavailable", "message": str(exc)},
            ) from exc
        except NoSpeechDetected as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "no_speech", "message": str(exc)},
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_audio", "message": str(exc)},
            ) from exc
    finally:
        if source:
            source.unlink(missing_ok=True)

    return ValidatedAudio(
        data=data,
        mime_type=declared,
        suffix=suffix,
        sha256=hashlib.sha256(data).hexdigest(),
        duration_seconds=round(duration, 3),
    )
