"""Real-audio integration verifier for Speaking S4 runtime.

Usage (from backend/):
    python scripts/verify_speaking_s4_real_audio.py

Optional env:
    SPEAKING_S4_REAL_AUDIO_FIXTURE=/path/to/speech.wav

Skips cleanly (exit 0 with SKIP message) when ffmpeg or faster_whisper unavailable.
"""

from __future__ import annotations

import asyncio
import math
import os
import sys
import tempfile
import wave
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_speaking.enums import SpeakingAudioSource  # noqa: E402
from app.services.language_speaking_audio_frontend.media_adapter import artifact_from_bytes  # noqa: E402
from app.services.language_speaking_audio_frontend.normalization_runtime import (  # noqa: E402
    _resolve_ffmpeg,
)
from app.services.language_speaking_audio_frontend.transcription_factory import (  # noqa: E402
    build_transcription_provider,
)
from app.services.language_speaking_evaluation_runtime.audio_runtime import process_speaking_audio  # noqa: E402

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_tone_wav(path: Path, *, seconds: float = 2.0, sample_rate: int = 16000) -> None:
    n = int(sample_rate * seconds)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(n):
            val = int(0.25 * 32767 * math.sin(2 * math.pi * 440.0 * (i / sample_rate)))
            wf.writeframesraw(val.to_bytes(2, "little", signed=True))


def _skip(msg: str) -> int:
    print(f"SKIP: {msg}")
    print("S4 REAL AUDIO — skipped (not a false PASS)")
    return 0


async def run_real_pipeline() -> int:
    print("Speaking S4 Real Audio Integration Verification\n")

    if not _resolve_ffmpeg():
        return _skip("ffmpeg not available")

    try:
        build_transcription_provider("faster_whisper")
    except Exception as exc:
        return _skip(f"faster_whisper provider unavailable: {exc}")

    fixture_env = os.environ.get("SPEAKING_S4_REAL_AUDIO_FIXTURE", "").strip()
    if fixture_env and Path(fixture_env).is_file():
        audio_path = Path(fixture_env)
        audio_bytes = audio_path.read_bytes()
        content_type = "audio/wav" if audio_path.suffix.lower() == ".wav" else "application/octet-stream"
        filename = audio_path.name
        input_format = f"fixture:{audio_path.suffix}"
    else:
        tmp = Path(tempfile.mkstemp(suffix=".wav")[1])
        try:
            _make_tone_wav(tmp, seconds=2.0, sample_rate=16000)
            audio_bytes = tmp.read_bytes()
        finally:
            tmp.unlink(missing_ok=True)
        content_type = "audio/wav"
        filename = "s4_qa_tone.wav"
        input_format = "generated:wav/16k/mono/tone440Hz"

    artifact = artifact_from_bytes(
        audio_id="audio_s4_real",
        session_id="session_s4_real",
        student_id=5,
        language_id=1,
        audio_bytes=audio_bytes,
        original_filename=filename,
        content_type=content_type,
        audio_source=SpeakingAudioSource.file_upload,
        captured_at=NOW,
    )

    result = await process_speaking_audio(
        artifact,
        audio_bytes,
        provider_name="faster_whisper",
        now=NOW,
    )

    print("=" * 60)
    print("S4 REAL AUDIO INTEGRATION REPORT")
    print("=" * 60)
    print(f"input_format: {input_format}")
    if result.normalized_artifact:
        n = result.normalized_artifact
        print(f"normalized_format: {n.container_format}/{n.codec}")
        print(f"sample_rate_hz: {n.sample_rate_hz}")
        print(f"channels: {n.channel_count}")
        print(f"duration_ms: {n.duration_ms}")
    else:
        print("normalized_format: (none — pipeline failed before normalization)")

    if result.success and result.bundle and result.bundle.transcript:
        tx = result.bundle.transcript
        prov = tx.provenance
        print(f"transcription_provider: {prov.provider_name if prov else 'unknown'}")
        print(f"model: {prov.model_name if prov else ''}")
        print(f"transcript: {tx.text!r}")
        print(f"evidence_availability: {result.bundle.evidence_availability}")
        print(f"warnings: {list(result.processing_warnings)}")
        print(f"word_count: {len(tx.words)}")
        print(f"segment_count: {len(tx.segments)}")
    else:
        print(f"pipeline_success: {result.success}")
        print(f"error: {result.error.code if result.error else 'none'}")
        print(f"session_state: {result.session.lifecycle_state.value}")
        print(f"warnings: {list(result.processing_warnings)}")
        if result.error and result.error.code == "empty_transcript":
            print("NOTE: synthetic tone WAV often yields empty transcript — pipeline still exercised.")
            print("S4 REAL AUDIO — pipeline exercised (normalization + transcription invoked)")
            return 0
        return 1

    print("S4 REAL AUDIO — VERIFIED")
    return 0


def main() -> int:
    return asyncio.run(run_real_pipeline())


if __name__ == "__main__":
    raise SystemExit(main())
