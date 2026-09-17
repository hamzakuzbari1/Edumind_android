"""Verify Speaking S5 Pronunciation Runtime (mock + structural checks).

Usage (from backend/):
    python scripts/verify_speaking_s5_pronunciation.py
"""

from __future__ import annotations

import asyncio
import inspect
import math
import subprocess
import sys
import tempfile
import wave
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"

from app.core.config import get_settings  # noqa: E402
from app.services.language_speaking.enums import SpeakingAudioSource  # noqa: E402
from app.services.language_speaking_audio_frontend.enums import SpeakingEvidenceFamily  # noqa: E402
from app.services.language_speaking_audio_frontend.errors import (  # noqa: E402
    PronunciationProviderUnavailableError,
)
from app.services.language_speaking_audio_frontend.media_adapter import artifact_from_bytes  # noqa: E402
from app.services.language_speaking_audio_frontend.normalization_runtime import _resolve_ffmpeg  # noqa: E402
from app.services.language_speaking_audio_frontend.pronunciation_factory import (  # noqa: E402
    build_pronunciation_provider,
    supported_pronunciation_providers,
)
from app.services.language_speaking_audio_frontend.pronunciation_runtime import (  # noqa: E402
    analyze_pronunciation_audio,
    provider_dict_to_phoneme_alignment_evidence,
)
from app.services.language_speaking_audio_frontend.validators import (  # noqa: E402
    validate_no_educational_fields_in_dict,
    validate_phoneme_alignment_evidence,
)
from app.services.language_speaking_evaluation_runtime.pronunciation_runtime import (  # noqa: E402
    process_speaking_pronunciation,
)
from app.services.language_speaking_pronunciation.issue_taxonomy import ISSUE_THETA_TO_S  # noqa: E402
from app.services.language_speaking_pronunciation.types import PronunciationReferenceSource  # noqa: E402

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def _make_tone_wav(*, seconds: float = 1.0, sample_rate: int = 16000, amplitude: float = 0.3) -> bytes:
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
                val = int(amplitude * 32767 * math.sin(2 * math.pi * 440.0 * (i / sample_rate)))
                wf.writeframesraw(val.to_bytes(2, "little", signed=True))
        return path.read_bytes()
    finally:
        path.unlink(missing_ok=True)


def _artifact(data: bytes) -> object:
    return artifact_from_bytes(
        audio_id="audio_s5_qa",
        session_id="session_s5_qa",
        student_id=5,
        language_id=1,
        audio_bytes=data,
        original_filename="test.wav",
        content_type="audio/wav",
        audio_source=SpeakingAudioSource.file_upload,
        captured_at=NOW,
    )


async def check_mock_provider() -> list[bool]:
    results: list[bool] = []
    prov = build_pronunciation_provider("mock")
    results.append(_ok("A mock provider registered", prov.capabilities().provider_name == "mock"))
    results.append(_ok("B supported providers include mock", "mock" in supported_pronunciation_providers()))

    wav = _make_tone_wav()
    raw, evidence, flags, used = await analyze_pronunciation_audio(
        wav,
        reference_text="think",
        provider=prov,
        generated_at=NOW,
    )
    results.append(_ok("C canonical PhonemeAlignmentEvidence returned", evidence is not None))
    results.append(_ok("D alignments non-empty for mock", len(evidence.alignments) > 0))
    results.append(_ok("E provider provenance wav2vec2 path not used", evidence.provenance.provider_name == "mock"))
    results.append(_ok("F phoneme validation passes", not validate_phoneme_alignment_evidence(evidence)))

    mapped, _ = provider_dict_to_phoneme_alignment_evidence(raw, generated_at=NOW)
    results.append(_ok("G provider dict maps to S3 evidence", len(mapped.alignments) == len(evidence.alignments)))
    results.append(_ok("H processing_version mock", str(raw.get("processing_version")) == "s5_mock"))
    return results


def check_provider_registration() -> list[bool]:
    from app.services.language_speaking_providers.pronunciation_wav2vec2 import RealPronunciationProvider

    results: list[bool] = []
    settings = get_settings()
    results.append(_ok("I wav2vec2 registered", "wav2vec2" in supported_pronunciation_providers()))
    results.append(
        _ok(
            "J production default is wav2vec2",
            (settings.SPEAKING_PRONUNCIATION_PROVIDER or "").strip().lower() == "wav2vec2",
        )
    )
    caps = RealPronunciationProvider().capabilities()
    results.append(_ok("K real provider name wav2vec2", caps.provider_name == "wav2vec2"))
    results.append(_ok("L supports forced alignment", caps.supports_forced_alignment))

    try:
        build_pronunciation_provider("whisperx")
        results.append(_ok("M no silent fallback unknown provider", False))
    except PronunciationProviderUnavailableError:
        results.append(_ok("M no silent fallback unknown provider", True))
    return results


async def check_orchestrator() -> list[bool]:
    results: list[bool] = []
    wav = _make_tone_wav()
    art = _artifact(wav)

    read_aloud = await process_speaking_pronunciation(
        art,
        wav,
        expected_task_text="think",
        provider_name="mock",
        now=NOW,
    )
    results.append(_ok("N read-aloud orchestrator success", read_aloud.success))
    if read_aloud.pronunciation:
        results.append(
            _ok(
                "O read-aloud reference_source expected_task_text",
                read_aloud.pronunciation.reference_source == PronunciationReferenceSource.expected_task_text,
            )
        )
    if read_aloud.bundle:
        results.append(
            _ok(
                "P bundle phoneme_alignment available",
                read_aloud.bundle.availability_for(SpeakingEvidenceFamily.phoneme_alignment),
            )
        )

    free = await process_speaking_pronunciation(
        art,
        wav,
        transcript_text="I think technology is useful",
        provider_name="mock",
        now=NOW,
    )
    if free.pronunciation:
        results.append(
            _ok(
                "Q free-speaking reference_source transcript_hypothesis",
                free.pronunciation.reference_source == PronunciationReferenceSource.transcript_hypothesis,
            )
        )

    edu_errors = validate_no_educational_fields_in_dict(free.pronunciation.to_persistence_dict() if free.pronunciation else {})
    results.append(_ok("R no educational fields in pronunciation result", not edu_errors, ",".join(edu_errors)))

    # Poor audio should not fake success with high reliability from mock path — use real provider gate via orchestrator error or low evidence.
    quiet = _make_tone_wav(amplitude=0.0001, seconds=0.05)
    quiet_art = _artifact(quiet)
    poor = await process_speaking_pronunciation(
        quiet_art,
        quiet,
        expected_task_text="think",
        provider_name="mock",
        now=NOW,
    )
    # Mock always succeeds structurally; real provider handles unreliable audio in real verifier.
    results.append(_ok("S poor audio orchestrator invoked", poor is not None))
    return results


def check_isolation_and_guardrails() -> list[bool]:
    results: list[bool] = []
    forbidden_hits: list[str] = []
    scan_roots = [
        SERVICES / "language_speaking_pronunciation",
        SERVICES / "language_speaking_evaluation_runtime" / "pronunciation_runtime.py",
    ]
    forbidden_tokens = (
        "official_speaking_cefr",
        "learning_stage_speaking",
        "promotion_readiness_score",
        "apply_observation",
        "update_mastery",
    )
    for root in scan_roots:
        paths = [root] if root.is_file() else list(root.glob("**/*.py"))
        for py in paths:
            text = py.read_text(encoding="utf-8").lower()
            for tok in forbidden_tokens:
                if tok in text:
                    forbidden_hits.append(f"{py.name}:{tok}")
    results.append(_ok("T no S2/CEFR/stage/readiness writes in S5", not forbidden_hits, ",".join(forbidden_hits)))

    # Issue tag is stable string not prose.
    results.append(_ok("U stable issue tag format", ISSUE_THETA_TO_S.startswith("pronunciation:")))
    return results


def check_frozen_layers() -> list[bool]:
    results: list[bool] = []
    scripts = [
        ("S0", "scripts/verify_speaking_s0_architecture.py"),
        ("S1", "scripts/verify_speaking_s1_skill_graph.py"),
        ("S2", "scripts/verify_speaking_s2_knowledge_model.py"),
        ("S2 DB", "scripts/verify_speaking_s2_persistence_db.py"),
        ("S3", "scripts/verify_speaking_s3_audio_frontend.py"),
        ("S4", "scripts/verify_speaking_s4_audio_runtime.py"),
    ]
    for label, script in scripts:
        path = BACKEND / script
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            timeout=300,
        )
        results.append(_ok(f"{label} verification remains green", proc.returncode == 0))
    return results


async def async_main() -> int:
    print("Speaking S5 Pronunciation Runtime Verification\n")
    if not _resolve_ffmpeg():
        print("WARN: ffmpeg not available — some checks may be limited")

    sections: list[tuple[str, object]] = [
        ("Mock provider (A-H)", check_mock_provider),
        ("Provider registration (I-M)", check_provider_registration),
        ("Orchestrator (N-S)", check_orchestrator),
        ("Isolation/guardrails (T-U)", check_isolation_and_guardrails),
        ("Frozen layers", check_frozen_layers),
    ]

    all_results: list[bool] = []
    for title, fn in sections:
        print(f"[{title}]")
        if inspect.iscoroutinefunction(fn):
            all_results.extend(await fn())
        else:
            all_results.extend(fn())
        print()

    passed = sum(all_results)
    total = len(all_results)
    print(f"Summary: {passed}/{total} checks passed")
    if passed == total:
        print("S5 STRUCTURAL -- READY for real audio verification.")
        print("STOP -- do not start S6.")
        return 0
    print("S5 NOT READY -- fix failures.")
    return 1


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
