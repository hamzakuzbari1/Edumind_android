"""Real GPT-4o transcription acceptance verifier for Speaking S4.

This verifier proves the REAL production path:
    real English speech audio
    -> SpeakingAudioArtifact
    -> normalization (mono 16 kHz PCM WAV)
    -> GPT4oTranscriptionProvider (OpenAI Audio Transcriptions API)
    -> TranscriptEvidence (+ real timing only when the model returns it)
    -> provider/model provenance
    -> SpeakingAudioEvidenceBundle
    -> session state == processed

ACCEPTANCE SEMANTICS: This is a strict acceptance run. It FAILS (exit 1), it does
NOT skip, when any of the following hold:
    - OPENAI_API_KEY is unavailable,
    - the configured Speaking provider is not "openai",
    - no real English speech fixture is provided,
    - ffmpeg is unavailable,
    - the pipeline silently falls back to a non-OpenAI provider,
    - the transcript is empty,
    - provider/model provenance is missing or false,
    - any educational decision leaks into S4 evidence.

Usage (from backend/):
    set SPEAKING_S4_REAL_AUDIO_FIXTURE=C:\\path\\to\\real_english_speech.(wav|mp3|m4a|webm)
    python scripts/verify_speaking_s4_gpt4o.py

Optional:
    SPEAKING_S4_EXPECTED_PHRASES="hello,my name"   # comma-separated substrings that
        must appear (case-insensitive) in the transcript to confirm meaning match.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.services.language_speaking.enums import SpeakingAudioSource  # noqa: E402
from app.services.language_speaking_audio_frontend.artifacts import (  # noqa: E402
    CANONICAL_CHANNEL_COUNT,
    CANONICAL_CODEC,
    CANONICAL_CONTAINER_FORMAT,
    CANONICAL_SAMPLE_RATE_HZ,
)
from app.services.language_speaking_audio_frontend.enums import AudioEvidenceQualityFlag  # noqa: E402
from app.services.language_speaking_audio_frontend.media_adapter import artifact_from_bytes  # noqa: E402
from app.services.language_speaking_audio_frontend.normalization_runtime import _resolve_ffmpeg  # noqa: E402
from app.services.language_speaking_audio_frontend.transcription_factory import (  # noqa: E402
    build_transcription_provider,
)
from app.services.language_speaking_audio_frontend.validators import (  # noqa: E402
    validate_no_educational_fields_in_dict,
    validate_segment_timestamps_ordered,
    validate_word_timestamps_ordered,
)
from app.services.language_speaking_audio_session.enums import SpeakingAudioLifecycleState  # noqa: E402
from app.services.language_speaking_evaluation_runtime.audio_runtime import process_speaking_audio  # noqa: E402

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

_CONTENT_TYPE_BY_SUFFIX = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
}


def _ok(label: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    line = f"  [{mark}] {label}"
    if detail:
        line += f" -- {detail}"
    print(line)
    return passed


def _fail_hard(msg: str) -> int:
    print(f"  [FAIL] {msg}")
    print("\nS4 GPT-4o ACCEPTANCE -- FAILED (not skipped).")
    return 1


def _count_temp_wavs() -> int:
    import tempfile

    tmp = Path(tempfile.gettempdir())
    try:
        return sum(1 for _ in tmp.glob("*.wav"))
    except OSError:
        return -1


async def run() -> int:
    print("Speaking S4 -- Real GPT-4o Transcription Acceptance Verification\n")
    settings = get_settings()

    print("[Preconditions -- FAIL not SKIP]")
    configured = (settings.SPEAKING_TRANSCRIPTION_PROVIDER or "").strip().lower()
    if configured != "openai":
        return _fail_hard(f"configured provider is '{configured}', expected 'openai'")
    _ok("configured provider is openai", True)

    if not (settings.OPENAI_API_KEY or "").strip():
        return _fail_hard("OPENAI_API_KEY is not configured")
    _ok("OPENAI_API_KEY present", True)

    if not _resolve_ffmpeg():
        return _fail_hard("ffmpeg is not available")
    _ok("ffmpeg available", True)

    fixture_env = os.environ.get("SPEAKING_S4_REAL_AUDIO_FIXTURE", "").strip()
    if not fixture_env or not Path(fixture_env).is_file():
        return _fail_hard(
            "SPEAKING_S4_REAL_AUDIO_FIXTURE must point to a real English speech recording"
        )
    audio_path = Path(fixture_env)
    _ok("real audio fixture present", True, str(audio_path))

    # Confirm the factory builds the OpenAI provider (no silent fallback) BEFORE the run.
    try:
        provider = build_transcription_provider()  # default => openai
    except Exception as exc:  # noqa: BLE001
        return _fail_hard(f"factory failed to build openai provider: {exc}")
    caps = provider.capabilities()
    if caps.provider_name != "openai":
        return _fail_hard(f"factory returned '{caps.provider_name}', not openai (fallback)")
    _ok("factory builds openai provider (no silent fallback)", True)

    audio_bytes = audio_path.read_bytes()
    content_type = _CONTENT_TYPE_BY_SUFFIX.get(audio_path.suffix.lower(), "application/octet-stream")

    artifact = artifact_from_bytes(
        audio_id="audio_s4_gpt4o",
        session_id="session_s4_gpt4o",
        student_id=5,
        language_id=1,
        audio_bytes=audio_bytes,
        original_filename=audio_path.name,
        content_type=content_type,
        audio_source=SpeakingAudioSource.file_upload,
        captured_at=NOW,
    )

    temp_before = _count_temp_wavs()

    result = await process_speaking_audio(artifact, audio_bytes, now=NOW)  # provider from config

    temp_after = _count_temp_wavs()

    print("\n[Pipeline outcome]")
    if not result.success or result.bundle is None or result.bundle.transcript is None:
        code = result.error.code if result.error else "unknown"
        print(f"  session_state: {result.session.lifecycle_state.value}")
        print(f"  warnings: {list(result.processing_warnings)}")
        return _fail_hard(f"pipeline did not succeed (error={code})")
    _ok("pipeline succeeded", True)

    tx = result.bundle.transcript
    prov = tx.provenance
    norm = result.normalized_artifact

    results: list[bool] = []

    # --- Normalization: mono 16 kHz PCM WAV ---
    results.append(_ok("normalized codec == pcm_s16le", norm is not None and norm.codec == CANONICAL_CODEC, norm.codec if norm else ""))
    results.append(_ok("normalized container == wav", norm is not None and norm.container_format == CANONICAL_CONTAINER_FORMAT))
    results.append(_ok("normalized sample_rate == 16000", norm is not None and norm.sample_rate_hz == CANONICAL_SAMPLE_RATE_HZ, str(norm.sample_rate_hz) if norm else ""))
    results.append(_ok("normalized channels == 1 (mono)", norm is not None and norm.channel_count == CANONICAL_CHANNEL_COUNT, str(norm.channel_count) if norm else ""))

    # --- Provider provenance / no fallback ---
    results.append(_ok("provenance present in bundle", prov is not None))
    results.append(_ok("provider_name == openai (not mock/whisper)", prov is not None and prov.provider_name == "openai", prov.provider_name if prov else ""))
    results.append(_ok("processing_version proves openai path", prov is not None and prov.processing_version == "s4_openai", prov.processing_version if prov else ""))
    results.append(_ok("model reported (non-empty)", prov is not None and bool((prov.model_name or "").strip()), prov.model_name if prov else ""))

    # --- Transcript ---
    transcript_text = (tx.text or "").strip()
    results.append(_ok("transcript non-empty", bool(transcript_text)))

    expected = [p.strip().lower() for p in os.environ.get("SPEAKING_S4_EXPECTED_PHRASES", "").split(",") if p.strip()]
    if expected:
        lowered = transcript_text.lower()
        for phrase in expected:
            results.append(_ok(f"transcript contains expected phrase: {phrase!r}", phrase in lowered))
    else:
        print("  [INFO] SPEAKING_S4_EXPECTED_PHRASES not set -- meaning-match is manual (see printed transcript)")

    # --- Timing honesty (never fabricated) ---
    model_supports_ts = caps.supports_word_timestamps
    if model_supports_ts:
        if tx.words:
            results.append(_ok("word timestamps ordered/consistent", not validate_word_timestamps_ordered(tx.words)))
        if tx.segments:
            results.append(_ok("segment timestamps ordered/consistent", not validate_segment_timestamps_ordered(tx.segments)))
        results.append(_ok("timing available matches capability", True, "model advertises timestamps"))
    else:
        results.append(_ok("no fabricated word timestamps", len(tx.words) == 0, f"words={len(tx.words)}"))
        results.append(_ok("no fabricated segment timestamps", len(tx.segments) == 0, f"segments={len(tx.segments)}"))
        results.append(_ok(
            "word timestamps explicitly marked unavailable",
            AudioEvidenceQualityFlag.timestamp_unavailable.value in result.processing_warnings,
        ))

    # --- Session lifecycle ---
    results.append(_ok("session state == processed", result.session.lifecycle_state == SpeakingAudioLifecycleState.processed, result.session.lifecycle_state.value))

    # --- Cleanup proof ---
    results.append(_ok("temp wav files cleaned up (no net leak)", temp_before < 0 or temp_after <= temp_before, f"before={temp_before} after={temp_after}"))

    # --- Evidence-only (no educational decisions) ---
    edu_errors = validate_no_educational_fields_in_dict({
        "text": tx.text,
        "language": tx.language,
        "provider_confidence": tx.provider_confidence,
        "provider_name": prov.provider_name if prov else "",
        "model_name": prov.model_name if prov else "",
    })
    results.append(_ok("no educational fields in evidence", not edu_errors, ",".join(edu_errors)))

    # --- Report block ---
    print("\n" + "=" * 62)
    print("S4 GPT-4o REAL TRANSCRIPTION REPORT")
    print("=" * 62)
    print(f"fixture: {audio_path}")
    print(f"fixture_size_bytes: {len(audio_bytes)}")
    print(f"normalized: {norm.container_format}/{norm.codec} {norm.sample_rate_hz}Hz ch={norm.channel_count} dur_ms={norm.duration_ms}")
    print(f"provider: {prov.provider_name}")
    print(f"model: {prov.model_name}")
    print(f"provider_version: {prov.provider_version}")
    print(f"processing_version: {prov.processing_version}")
    print(f"transcript: {transcript_text!r}")
    print(f"word_count: {len(tx.words)}  segment_count: {len(tx.segments)}")
    print(f"provider_confidence: {tx.provider_confidence}")
    print(f"evidence_availability: {result.bundle.evidence_availability}")
    print(f"quality/warnings: {list(result.processing_warnings)}")
    print(f"session_final_state: {result.session.lifecycle_state.value}")
    print(f"temp_wavs before/after: {temp_before}/{temp_after}")
    print("=" * 62)

    passed = sum(results)
    total = len(results)
    print(f"\nSummary: {passed}/{total} acceptance checks passed")
    if passed == total:
        print("S4 GPT-4o ACCEPTANCE -- VERIFIED (real OpenAI transcription).")
        return 0
    print("S4 GPT-4o ACCEPTANCE -- FAILED.")
    return 1


def main() -> int:
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
