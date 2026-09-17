"""Content-aware, bounded validation tests for placement speaking audio."""

from __future__ import annotations

import asyncio
import hashlib
import io
import wave
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.services import language_audio_security_service as audio_security


def _upload(data: bytes, content_type: str = "audio/wav") -> UploadFile:
    return UploadFile(
        io.BytesIO(data),
        filename="answer.wav",
        headers=Headers({"content-type": content_type}),
    )


def _wav_bytes(*, amplitude: int, seconds: float = 0.5, sample_rate: int = 16_000) -> bytes:
    output = io.BytesIO()
    frame_count = int(seconds * sample_rate)
    sample = int(amplitude).to_bytes(2, byteorder="little", signed=True)
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(sample * frame_count)
    return output.getvalue()


def _decode_wav_without_ffmpeg(monkeypatch):
    monkeypatch.setattr(audio_security, "_normalize_to_wav_16k", lambda source: source)


def test_valid_audio_is_content_sniffed_hashed_and_decoded(monkeypatch):
    _decode_wav_without_ffmpeg(monkeypatch)
    data = _wav_bytes(amplitude=1_000)

    result = asyncio.run(audio_security.validate_placement_audio(_upload(data)))

    assert result.mime_type == "audio/wav"
    assert result.suffix == ".wav"
    assert result.sha256 == hashlib.sha256(data).hexdigest()
    assert result.duration_seconds == pytest.approx(0.5)


def test_silent_audio_is_rejected_before_stt_or_scoring(monkeypatch):
    _decode_wav_without_ffmpeg(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            audio_security.validate_placement_audio(
                _upload(_wav_bytes(amplitude=0, seconds=0.6))
            )
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "no_speech"
    assert "speech signal" in exc_info.value.detail["message"]


def test_declared_mime_must_match_the_actual_file_signature():
    wav_data = _wav_bytes(amplitude=1_000)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            audio_security.validate_placement_audio(
                _upload(wav_data, content_type="audio/mpeg")
            )
        )

    assert exc_info.value.status_code == 415
    assert exc_info.value.detail["code"] == "audio_type_mismatch"


def test_unknown_bytes_are_rejected_even_with_an_audio_extension_and_mime():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            audio_security.validate_placement_audio(
                _upload(b"this is not an audio file", content_type="audio/wav")
            )
        )

    assert exc_info.value.status_code == 415
    assert exc_info.value.detail["code"] == "audio_type_mismatch"


def test_oversized_audio_is_rejected_by_a_bounded_chunked_read(monkeypatch):
    monkeypatch.setattr(
        audio_security,
        "get_settings",
        lambda: SimpleNamespace(GENAI_EXAM_MAX_AUDIO_MB=1),
    )
    oversized = b"RIFF" + b"\x00" * (1024 * 1024 + 1)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(audio_security.validate_placement_audio(_upload(oversized)))

    assert exc_info.value.status_code == 413
    assert exc_info.value.detail["code"] == "audio_too_large"


def test_empty_audio_is_rejected():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(audio_security.validate_placement_audio(_upload(b"")))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "empty_audio"
