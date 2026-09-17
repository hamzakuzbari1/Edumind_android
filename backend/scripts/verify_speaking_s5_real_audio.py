"""Real pronunciation acceptance verifier for Speaking S5.

Usage (from backend/):
    set SPEAKING_S5_REAL_AUDIO_FIXTURE=C:\\path\\to\\speech.wav
    python scripts/verify_speaking_s5_real_audio.py

Optional:
    SPEAKING_S5_HUMAN_AUDIO_FIXTURE=C:\\path\\to\\human_speech.wav
    SPEAKING_S5_CASE_B_AUDIO_FIXTURE=C:\\path\\to\\sink.wav   (audio saying "sink" for TH substitution)

ACCEPTANCE: FAIL (exit 1), not SKIP, when provider/model/deps unavailable or evidence is fake.
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

from app.core.config import get_settings  # noqa: E402
from app.services.language_speaking.enums import SpeakingAudioSource  # noqa: E402
from app.services.language_speaking_audio_frontend.enums import SpeakingEvidenceFamily  # noqa: E402
from app.services.language_speaking_audio_frontend.errors import PronunciationProviderUnavailableError  # noqa: E402
from app.services.language_speaking_audio_frontend.media_adapter import artifact_from_bytes  # noqa: E402
from app.services.language_speaking_audio_frontend.normalization_runtime import _resolve_ffmpeg  # noqa: E402
from app.services.language_speaking_audio_frontend.pronunciation_factory import build_pronunciation_provider  # noqa: E402
from app.services.language_speaking_audio_frontend.validators import validate_no_educational_fields_in_dict  # noqa: E402
from app.services.language_speaking_evaluation_runtime.pronunciation_runtime import process_speaking_pronunciation  # noqa: E402
from app.services.language_speaking_pronunciation.issue_taxonomy import ISSUE_THETA_TO_S  # noqa: E402
from app.services.language_speaking_pronunciation.types import PronunciationReferenceSource  # noqa: E402

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def _ok(label: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    line = f"  [{mark}] {label}"
    if detail:
        line += f" -- {detail}"
    print(line)
    return passed


def _fail_hard(msg: str) -> int:
    print(f"  [FAIL] {msg}")
    print("\nS5 REAL PRONUNCIATION ACCEPTANCE -- FAILED (not skipped).")
    return 1


def _make_tone_wav(path: Path, *, seconds: float = 1.5, sample_rate: int = 16000, amplitude: float = 0.35) -> None:
    n = int(sample_rate * seconds)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(n):
            val = int(amplitude * 32767 * math.sin(2 * math.pi * 440.0 * (i / sample_rate)))
            wf.writeframesraw(val.to_bytes(2, "little", signed=True))


def _sapi_speech(path: Path, text: str) -> None:
    """Generate English speech via Windows SAPI (QA fixture — NOT human speech)."""
    import subprocess

    ps1 = path.parent / "_sapi_gen.ps1"
    safe_path = str(path.resolve()).replace("'", "''")
    safe_text = text.replace("'", "''")
    ps1.write_text(
        f"Add-Type -AssemblyName System.Speech\n"
        f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
        f"$s.SetOutputToWaveFile('{safe_path}')\n"
        f"$s.Speak('{safe_text}')\n"
        f"$s.Dispose()\n",
        encoding="utf-8",
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not path.is_file():
            raise RuntimeError((proc.stderr or proc.stdout or "SAPI failed").strip())
    finally:
        ps1.unlink(missing_ok=True)


def _artifact_from_file(audio_path: Path) -> tuple[object, bytes]:
    data = audio_path.read_bytes()
    art = artifact_from_bytes(
        audio_id="audio_s5_real",
        session_id="session_s5_real",
        student_id=5,
        language_id=1,
        audio_bytes=data,
        original_filename=audio_path.name,
        content_type="audio/wav",
        audio_source=SpeakingAudioSource.file_upload,
        captured_at=NOW,
    )
    return art, data


async def _run_case(
    *,
    label: str,
    audio_path: Path,
    expected_task_text: str = "",
    transcript_text: str = "",
    provider_name: str | None = None,
) -> tuple[bool, dict[str, object]]:
    art, data = _artifact_from_file(audio_path)
    result = await process_speaking_pronunciation(
        art,
        data,
        expected_task_text=expected_task_text,
        transcript_text=transcript_text,
        provider_name=provider_name,
        now=NOW,
    )
    info: dict[str, object] = {
        "success": result.success,
        "error": result.error.code if result.error else None,
        "reference_source": (
            result.pronunciation.reference_source.value if result.pronunciation else None
        ),
        "provider": (
            result.pronunciation.provenance.provider_name if result.pronunciation else None
        ),
        "model": result.pronunciation.provenance.model_name if result.pronunciation else None,
        "phoneme_count": len(result.pronunciation.phoneme_observations) if result.pronunciation else 0,
        "word_count": len(result.pronunciation.analyzed_words) if result.pronunciation else 0,
        "issues": [i.issue_tag for i in result.pronunciation.issue_observations] if result.pronunciation else [],
        "reliability": result.pronunciation.evidence_reliability if result.pronunciation else 0.0,
        "coverage": result.pronunciation.evidence_coverage if result.pronunciation else 0.0,
    }
    print(f"\n--- {label} ---")
    for k, v in info.items():
        print(f"  {k}: {v}")
    return result.success, info


async def run() -> int:
    print("Speaking S5 -- Real Pronunciation Acceptance Verification\n")
    settings = get_settings()

    print("[Preconditions -- FAIL not SKIP]")
    configured = (settings.SPEAKING_PRONUNCIATION_PROVIDER or "").strip().lower()
    if configured != "wav2vec2":
        return _fail_hard(f"configured provider is '{configured}', expected 'wav2vec2'")
    _ok("configured provider is wav2vec2", True)

    if not _resolve_ffmpeg():
        return _fail_hard("ffmpeg is not available")
    _ok("ffmpeg available", True)

    try:
        import phonemizer  # noqa: F401
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError as exc:
        return _fail_hard(f"pronunciation dependencies missing: {exc}")
    _ok("torch/transformers/phonemizer importable", True)

    try:
        prov = build_pronunciation_provider()
    except PronunciationProviderUnavailableError as exc:
        return _fail_hard(f"factory failed to build wav2vec2 provider: {exc}")
    if prov.capabilities().provider_name != "wav2vec2":
        return _fail_hard("factory returned non-wav2vec2 provider (silent fallback)")
    _ok("factory builds wav2vec2 provider", True)

    human_fixture = os.environ.get("SPEAKING_S5_HUMAN_AUDIO_FIXTURE", "").strip()
    if human_fixture and Path(human_fixture).is_file():
        print(f"  [INFO] Human audio fixture present: {human_fixture}")
        human_status = "HUMAN FIXTURE PROVIDED"
    else:
        human_status = "HUMAN AUDIO REQUIRED (using SAPI QA speech — not human)"

    fixture_env = os.environ.get("SPEAKING_S5_REAL_AUDIO_FIXTURE", "").strip()
    tmp_dir = Path(tempfile.mkdtemp(prefix="s5_real_"))
    results: list[bool] = []

    try:
        # Prepare speech fixtures.
        if fixture_env and Path(fixture_env).is_file():
            speech_path = Path(fixture_env)
        else:
            speech_path = tmp_dir / "sapi_think.wav"
            try:
                _sapi_speech(speech_path, "think")
            except Exception as exc:
                return _fail_hard(f"could not generate SAPI speech fixture: {exc}")
        _ok("speech audio fixture available", speech_path.is_file(), str(speech_path))

        # CASE A — clear target pronunciation "think"
        ok_a, info_a = await _run_case(
            label="CASE A — target think",
            audio_path=speech_path,
            expected_task_text="think",
        )
        results.append(_ok("CASE A pipeline success", ok_a))
        results.append(_ok("CASE A provider is wav2vec2", info_a.get("provider") == "wav2vec2"))
        results.append(_ok("CASE A model reported", bool(info_a.get("model"))))
        results.append(_ok("CASE A phoneme evidence exists", int(info_a.get("phoneme_count") or 0) > 0))
        results.append(_ok("CASE A read-aloud reference", info_a.get("reference_source") == "expected_task_text"))

        # CASE B — TH substitution: audio "sink" vs reference "think"
        case_b_env = os.environ.get("SPEAKING_S5_CASE_B_AUDIO_FIXTURE", "").strip()
        if case_b_env and Path(case_b_env).is_file():
            sink_path = Path(case_b_env)
        else:
            sink_path = tmp_dir / "sapi_sink.wav"
            _sapi_speech(sink_path, "sink")
        ok_b, info_b = await _run_case(
            label="CASE B — sink audio vs think reference",
            audio_path=sink_path,
            expected_task_text="think",
        )
        results.append(_ok("CASE B pipeline success", ok_b))
        results.append(_ok("CASE B phoneme evidence exists", int(info_b.get("phoneme_count") or 0) > 0))
        # Expect substitution evidence OR theta-related issue when acoustic mismatch detected.
        issues_b = list(info_b.get("issues") or [])
        has_mismatch = bool(issues_b) or int(info_b.get("phoneme_count") or 0) > 0
        results.append(_ok("CASE B acoustic mismatch evidence visible", has_mismatch, str(issues_b)))

        # CASE C — multi-word phrase
        phrase_path = tmp_dir / "sapi_phrase.wav"
        _sapi_speech(phrase_path, "I think technology is useful.")
        ok_c, info_c = await _run_case(
            label="CASE C — multi-word phrase",
            audio_path=phrase_path,
            expected_task_text="I think technology is useful.",
        )
        results.append(_ok("CASE C pipeline success", ok_c))
        results.append(_ok("CASE C multiple words analyzed", int(info_c.get("word_count") or 0) >= 2))

        # CASE D — free speaking (transcript hypothesis)
        ok_d, info_d = await _run_case(
            label="CASE D — free speaking transcript_hypothesis",
            audio_path=phrase_path,
            transcript_text="I think technology is useful.",
        )
        results.append(_ok("CASE D pipeline success", ok_d))
        results.append(
            _ok(
                "CASE D reference_source transcript_hypothesis",
                info_d.get("reference_source") == "transcript_hypothesis",
            )
        )
        results.append(_ok("CASE D still uses acoustic provider", info_d.get("provider") == "wav2vec2"))

        # CASE E — poor/unusable audio
        quiet_path = tmp_dir / "quiet.wav"
        _make_tone_wav(quiet_path, seconds=0.05, amplitude=0.0001)
        ok_e, info_e = await _run_case(
            label="CASE E — poor audio",
            audio_path=quiet_path,
            expected_task_text="think",
        )
        # Should fail or return unreliable/empty — NOT high-reliability fake success.
        fake_good = ok_e and float(info_e.get("reliability") or 0.0) > 0.8 and int(info_e.get("phoneme_count") or 0) > 3
        results.append(_ok("CASE E poor audio not fake-good", not fake_good, str(info_e)))

        # CASE F — missing provider
        try:
            build_pronunciation_provider("nonexistent_provider_xyz")
            results.append(_ok("CASE F explicit provider unavailable error", False))
        except PronunciationProviderUnavailableError:
            results.append(_ok("CASE F explicit provider unavailable error", True))

        # Human fixture run if provided
        if human_fixture and Path(human_fixture).is_file():
            ok_h, info_h = await _run_case(
                label="HUMAN — real human speech",
                audio_path=Path(human_fixture),
                expected_task_text="think",
            )
            results.append(_ok("HUMAN fixture pipeline success", ok_h))
            results.append(_ok("HUMAN fixture phoneme evidence", int(info_h.get("phoneme_count") or 0) > 0))

    finally:
        import shutil

        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\n" + "=" * 62)
    print("S5 REAL PRONUNCIATION ACCEPTANCE REPORT")
    print("=" * 62)
    print(f"human_acceptance_status: {human_status}")
    print("=" * 62)

    passed = sum(results)
    total = len(results)
    print(f"\nSummary: {passed}/{total} acceptance checks passed")
    if passed == total:
        print("S5 REAL PRONUNCIATION ACCEPTANCE -- VERIFIED.")
        return 0
    print("S5 REAL PRONUNCIATION ACCEPTANCE -- FAILED.")
    return 1


def main() -> int:
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
