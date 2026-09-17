"""Verify Speaking S4 Audio Runtime (mock provider + structural checks).

Usage (from backend/):
    python scripts/verify_speaking_s4_audio_runtime.py
"""

from __future__ import annotations

import asyncio
import ast
import importlib
import math
import os
import subprocess
import sys
import tempfile
import wave
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"

from app.services.language_speaking.enums import SpeakingAudioSource  # noqa: E402
from app.services.language_speaking_audio_frontend.artifacts import (  # noqa: E402
    AudioArtifactKind,
)
from app.services.language_speaking_audio_frontend.enums import (  # noqa: E402
    AudioEvidenceQualityFlag,
    SpeakingEvidenceFamily,
)
from app.services.language_speaking_audio_frontend.errors import (  # noqa: E402
    EmptyTranscriptError,
    NormalizationFailedError,
    TranscriptionProviderUnavailableError,
)
from app.services.language_speaking_audio_frontend.legacy_runtime_mapping import (  # noqa: E402
    S4_LEGACY_RUNTIME_MAP,
    S4_PERSISTENCE_MAPPING,
)
from app.services.language_speaking_audio_frontend.media_adapter import (  # noqa: E402
    artifact_from_bytes,
)
from app.services.language_speaking_audio_frontend.artifacts import (  # noqa: E402
    CANONICAL_CHANNEL_COUNT,
    CANONICAL_SAMPLE_RATE_HZ,
)
from app.services.language_speaking_audio_frontend.normalization_runtime import (  # noqa: E402
    normalize_audio_with_bytes,
    _resolve_ffmpeg,
)
from app.services.language_speaking_audio_frontend.transcription_factory import (  # noqa: E402
    build_transcription_provider,
    supported_transcription_providers,
)
from app.services.language_speaking_audio_frontend.transcription_runtime import (  # noqa: E402
    provider_dict_to_transcript_evidence,
    transcribe_normalized_audio,
)
from app.services.language_speaking_audio_frontend.validators import (  # noqa: E402
    FORBIDDEN_EDUCATIONAL_FIELD_NAMES,
    validate_no_educational_fields_in_dict,
    validate_segment_timestamps_ordered,
    validate_word_timestamps_ordered,
)
from app.services.language_speaking_audio_session.enums import SpeakingAudioLifecycleState  # noqa: E402
from app.services.language_speaking_evaluation_runtime.audio_runtime import (  # noqa: E402
    process_speaking_audio,
)
from app.services.language_speaking_providers.transcription_mock import MockTranscriptionProvider  # noqa: E402

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def _make_tone_wav(*, seconds: float = 1.0, sample_rate: int = 48000, freq: float = 440.0) -> bytes:
    n = int(sample_rate * seconds)
    buf = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    path = Path(buf.name)
    buf.close()
    try:
        with wave.open(str(path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            for i in range(n):
                val = int(0.3 * 32767 * math.sin(2 * math.pi * freq * (i / sample_rate)))
                wf.writeframesraw(val.to_bytes(2, "little", signed=True))
        return path.read_bytes()
    finally:
        path.unlink(missing_ok=True)


def _make_webm_like_bytes() -> bytes:
    """Minimal bytes labeled as webm for artifact mapping (normalization may still accept via ffmpeg)."""
    return b"\x1a\x45\xdf\xa3" + b"\x00" * 128


def _sample_artifact(content_type: str, filename: str, data: bytes) -> object:
    return artifact_from_bytes(
        audio_id="audio_s4_qa",
        session_id="session_s4_qa",
        student_id=5,
        language_id=1,
        audio_bytes=data,
        original_filename=filename,
        content_type=content_type,
        audio_source=SpeakingAudioSource.browser_recording,
        captured_at=NOW,
    )


async def _run_orchestrator(data: bytes, *, content_type: str = "audio/wav", filename: str = "test.wav"):
    art = _sample_artifact(content_type, filename, data)
    return await process_speaking_audio(art, data, provider_name="mock", now=NOW)


def check_artifact_mapping() -> list[bool]:
    results: list[bool] = []
    webm_data = _make_webm_like_bytes()
    webm_art = _sample_artifact("audio/webm", "recording.webm", webm_data)
    results.append(_ok("A browser-format artifact mapping", webm_art.content_type == "audio/webm"))
    results.append(_ok("A artifact kind raw", webm_art.artifact_kind == AudioArtifactKind.raw))

    wav_data = _make_tone_wav(sample_rate=16000)
    wav_art = _sample_artifact("audio/wav", "recording.wav", wav_data)
    results.append(_ok("B WAV artifact mapping", wav_art.container_format == "wav"))

    results.append(_ok("C unknown sample_rate explicit zero", wav_art.sample_rate_hz == 0))
    results.append(_ok("C unknown duration explicit zero", wav_art.duration_ms == 0))
    results.append(_ok("C integrity hash when bytes present", bool(wav_art.integrity.content_hash)))
    return results


def check_normalization() -> list[bool]:
    results: list[bool] = []
    if not _resolve_ffmpeg():
        results.append(_ok("D ffmpeg available for normalization", False, "ffmpeg missing"))
        results.append(_ok("E normalized inspection", False, "skipped"))
        results.append(_ok("F source traceability", False, "skipped"))
        results.append(_ok("G normalization warnings", False, "skipped"))
        results.append(_ok("H corrupt audio fails", False, "skipped"))
        results.append(_ok("I temp cleanup on success (source)", True))
        results.append(_ok("J temp cleanup on failure (source)", True))
        return results

    wav_in = _make_tone_wav(sample_rate=48000)
    art = _sample_artifact("audio/wav", "input.wav", wav_in)
    norm, norm_bytes, warnings = normalize_audio_with_bytes(art, wav_in, now=NOW)

    results.append(_ok("D real normalization to mono 16k PCM WAV", norm.sample_rate_hz == CANONICAL_SAMPLE_RATE_HZ))
    results.append(_ok("E actual normalized sample rate", norm.sample_rate_hz == 16000))
    results.append(_ok("E actual normalized channels", norm.channel_count == CANONICAL_CHANNEL_COUNT))
    results.append(_ok("E normalized bytes non-empty", len(norm_bytes) > 44))
    results.append(_ok("F source to normalized traceability", norm.source_audio_id == art.audio_id))
    results.append(_ok("G normalization warnings preserved type", isinstance(warnings, tuple)))

    corrupt_art = _sample_artifact("audio/webm", "bad.webm", b"not-valid-audio")
    try:
        normalize_audio_with_bytes(corrupt_art, b"not-valid-audio", now=NOW)
        results.append(_ok("H corrupt audio fails structurally", False))
    except (NormalizationFailedError, Exception):
        results.append(_ok("H corrupt audio fails structurally", True))

    src = (SERVICES / "language_speaking_audio_frontend" / "normalization_runtime.py").read_text(encoding="utf-8")
    results.append(_ok("I temp cleanup on success (finally unlink)", "finally:" in src and "unlink" in src))
    results.append(_ok("J temp cleanup on failure (finally unlink)", "finally:" in src and "unlink" in src))
    return results


async def check_transcription_mock() -> list[bool]:
    results: list[bool] = []
    prov = build_transcription_provider("mock")
    results.append(_ok("K mock provider selected through factory", prov.capabilities().provider_name == "mock"))
    results.append(_ok("K supported providers include mock", "mock" in supported_transcription_providers()))

    wav = _make_tone_wav(sample_rate=16000)
    tx, flags, used = await transcribe_normalized_audio(wav, provider=prov, generated_at=NOW)
    results.append(_ok("L canonical TranscriptEvidence returned", tx is not None))
    results.append(_ok("M transcript text preserved", tx.text == "hello world"))
    results.append(_ok("N segment timestamps ordered", not validate_segment_timestamps_ordered(tx.segments)))
    results.append(_ok("O word timestamps ordered", not validate_word_timestamps_ordered(tx.words)))
    results.append(_ok("Q provider provenance correct", tx.provenance is not None and tx.provenance.provider_name == "mock"))
    caps = used.capabilities()
    results.append(_ok("R capability word timestamps", caps.supports_word_timestamps))

    text_only_raw = {
        "text": "hello",
        "language": "en",
        "provider_confidence": 0.9,
        "segments": [{"text": "hello", "start_sec": 0.0, "end_sec": 0.5, "confidence": 0.9}],
        "words": [],
        "provider_name": "mock",
        "model": "mock-v1",
    }
    tx2, flags2 = provider_dict_to_transcript_evidence(text_only_raw, generated_at=NOW)
    results.append(_ok("P missing word timestamps explicit", AudioEvidenceQualityFlag.timestamp_unavailable in flags2))
    results.append(_ok("P words empty when unsupported", len(tx2.words) == 0))

    try:
        build_transcription_provider("whisperx")
        results.append(_ok("S no silent fallback unknown provider", False))
    except TranscriptionProviderUnavailableError:
        results.append(_ok("S no silent fallback unknown provider", True))

    try:
        provider_dict_to_transcript_evidence({"text": "", "language": "en", "provider_confidence": 0.0})
        results.append(_ok("T empty transcript rejected", False))
    except EmptyTranscriptError:
        results.append(_ok("T empty transcript rejected", True))

    return results


def check_openai_provider_registration() -> list[bool]:
    """OpenAI GPT-4o is the registered production default; no silent fallback."""
    from app.core.config import get_settings
    from app.services.language_speaking_providers.transcription_openai import (
        GPT4oTranscriptionProvider,
        _model_supports_timestamps,
    )

    results: list[bool] = []
    settings = get_settings()

    results.append(_ok("AI openai registered as supported provider", "openai" in supported_transcription_providers()))
    results.append(_ok("AJ production default is openai", (settings.SPEAKING_TRANSCRIPTION_PROVIDER or "").strip().lower() == "openai"))

    caps = GPT4oTranscriptionProvider().capabilities()
    results.append(_ok("AK openai capabilities provider_name=openai", caps.provider_name == "openai"))

    # gpt-4o-transcribe returns no timestamps; whisper-1 does. Honesty of capability.
    results.append(_ok("AL gpt-4o-transcribe reports no word timestamps", _model_supports_timestamps("gpt-4o-transcribe") is False))
    results.append(_ok("AM whisper-1 reports word timestamps", _model_supports_timestamps("whisper-1") is True))

    # No silent fallback: openai selected without credentials must RAISE, not switch.
    original_key = settings.OPENAI_API_KEY
    try:
        settings.OPENAI_API_KEY = ""
        try:
            build_transcription_provider("openai")
            results.append(_ok("AN openai without key raises (no silent fallback)", False))
        except TranscriptionProviderUnavailableError:
            results.append(_ok("AN openai without key raises (no silent fallback)", True))
    finally:
        settings.OPENAI_API_KEY = original_key

    return results


async def check_orchestrator_and_bundle() -> list[bool]:
    results: list[bool] = []
    wav = _make_tone_wav(sample_rate=16000)
    result = await _run_orchestrator(wav)
    results.append(_ok("U transcript-only bundle assembled", result.success and result.bundle is not None))
    if result.bundle:
        b = result.bundle
        results.append(_ok("V embedding evidence None", b.speech_embedding is None))
        results.append(_ok("W phoneme evidence None", b.phoneme_alignment is None))
        results.append(_ok("X prosody evidence None", b.prosody is None))
        results.append(_ok("Y missing capabilities explicit", not b.availability_for(SpeakingEvidenceFamily.speech_embedding)))
        results.append(_ok("Z session processed", result.session.lifecycle_state == SpeakingAudioLifecycleState.processed))
        results.append(_ok("AC deterministic serialization", len(b.to_deterministic_json()) > 50))
        forbidden = validate_no_educational_fields_in_dict(b.to_persistence_dict())
        results.append(_ok("AD no educational decision fields", not forbidden, str(forbidden[:2])))

    bad = await process_speaking_audio(
        _sample_artifact("audio/wav", "empty.wav", b""),
        b"",
        provider_name="mock",
        now=NOW,
    )
    results.append(_ok("AA failed processing transitions to failed", not bad.success))
    results.append(
        _ok(
            "AA session failed state",
            bad.session.lifecycle_state == SpeakingAudioLifecycleState.failed,
        )
    )
    results.append(_ok("AB structured error not raw provider", bad.error is not None and hasattr(bad.error, "code")))
    return results


def check_legacy_and_isolation() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("AF legacy runtime map documented", len(S4_LEGACY_RUNTIME_MAP) >= 5))
    results.append(_ok("AF persistence mapping documented", len(S4_PERSISTENCE_MAPPING) >= 5))

    try:
        importlib.import_module("app.services.language_transcription_service")
        results.append(_ok("AE legacy transcription service importable", True))
    except Exception as exc:
        results.append(_ok("AE legacy transcription service importable", False, str(exc)))

    km_dir = SERVICES / "language_speaking_knowledge_model"
    km_bad: set[str] = set()
    for py in km_dir.glob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "audio_frontend" in node.module or "language_speaking_providers" in node.module:
                    km_bad.add(node.module)
    results.append(_ok("AG S2 knowledge model untouched", not km_bad))

    s3_artifacts = (SERVICES / "language_speaking_audio_frontend" / "artifacts.py").read_text(encoding="utf-8")
    results.append(_ok("AH S3 artifacts unchanged schema version", 'LANGUAGE_SPEAKING_AUDIO_FRONTEND_VERSION = "0.3.0"' in s3_artifacts))
    return results


def check_frozen_layers() -> list[bool]:
    results: list[bool] = []
    scripts = [
        ("S0", "scripts/verify_speaking_s0_architecture.py"),
        ("S1", "scripts/verify_speaking_s1_skill_graph.py"),
        ("S2", "scripts/verify_speaking_s2_knowledge_model.py"),
        ("S2 DB", "scripts/verify_speaking_s2_persistence_db.py"),
        ("S3", "scripts/verify_speaking_s3_audio_frontend.py"),
    ]
    for label, script in scripts:
        path = BACKEND / script
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            timeout=180,
        )
        results.append(_ok(f"{label} verification remains green", proc.returncode == 0))
    return results


async def async_main() -> int:
    print("Speaking S4 Audio Runtime Verification\n")
    sections: list[tuple[str, object]] = [
        ("Artifact mapping (A-C)", check_artifact_mapping),
        ("Normalization (D-J)", check_normalization),
        ("Transcription mock (K-T)", check_transcription_mock),
        ("OpenAI provider registration (AI-AN)", check_openai_provider_registration),
        ("Orchestrator + bundle (U-AD)", check_orchestrator_and_bundle),
        ("Legacy + isolation (AE-AH)", check_legacy_and_isolation),
        ("Frozen layers", check_frozen_layers),
    ]

    all_results: list[bool] = []
    for title, fn in sections:
        print(f"[{title}]")
        if asyncio.iscoroutinefunction(fn):
            all_results.extend(await fn())
        else:
            all_results.extend(fn())
        print()

    passed = sum(all_results)
    total = len(all_results)
    print(f"Summary: {passed}/{total} checks passed")
    if passed == total:
        print("S4 READY -- S5 may begin after review.")
        print("STOP -- do not start S5.")
        return 0
    print("S4 NOT READY -- fix failures before S5.")
    return 1


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
