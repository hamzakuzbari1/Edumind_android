"""Verify Speaking S6 Prosody Runtime (mock + structural checks).

Usage (from backend/):
    python scripts/verify_speaking_s6_prosody.py
"""

from __future__ import annotations

import asyncio
import inspect
import json
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
from app.services.language_speaking.ownership import ALLOWED_PACKAGE_DEPENDENCIES  # noqa: E402
from app.services.language_speaking_audio_frontend.enums import SpeakingEvidenceFamily  # noqa: E402
from app.services.language_speaking_audio_frontend.errors import (  # noqa: E402
    ProsodyProviderUnavailableError,
)
from app.services.language_speaking_audio_frontend.media_adapter import artifact_from_bytes  # noqa: E402
from app.services.language_speaking_audio_frontend.normalization_runtime import _resolve_ffmpeg  # noqa: E402
from app.services.language_speaking_audio_frontend.prosody_factory import (  # noqa: E402
    build_prosody_provider,
    supported_prosody_providers,
)
from app.services.language_speaking_audio_frontend.prosody_runtime import (  # noqa: E402
    analyze_prosody_audio,
    provider_dict_to_prosody_evidence,
)
from app.services.language_speaking_audio_frontend.validators import (  # noqa: E402
    validate_no_educational_fields_in_dict,
    validate_prosody_evidence,
)
from app.services.language_speaking_evaluation_runtime.pronunciation_runtime import (  # noqa: E402
    process_speaking_pronunciation,
)
from app.services.language_speaking_evaluation_runtime.prosody_runtime import process_speaking_prosody  # noqa: E402
from app.services.language_speaking_prosody.expression_mapping import normalize_expression_label  # noqa: E402
from app.services.language_speaking_prosody.issue_taxonomy import ALL_PROSODY_ISSUE_TAGS  # noqa: E402
from app.services.language_speaking_prosody.types import ProsodyEvidenceSource  # noqa: E402
from app.services.language_speaking_providers.acoustic_derive import derive_acoustic_prosody  # noqa: E402

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def _make_tone_wav(*, seconds: float = 1.2, sample_rate: int = 16000, amplitude: float = 0.3) -> bytes:
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


def _artifact(data: bytes, audio_id: str = "audio_s6_qa") -> object:
    return artifact_from_bytes(
        audio_id=audio_id,
        session_id="session_s6_qa",
        student_id=6,
        language_id=1,
        audio_bytes=data,
        original_filename="test.wav",
        content_type="audio/wav",
        audio_source=SpeakingAudioSource.file_upload,
        captured_at=NOW,
    )


async def check_capability_discovery() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("A supported providers discovered", len(supported_prosody_providers()) >= 2))
    prov = build_prosody_provider("mock")
    caps = prov.capabilities()
    results.append(_ok("B mock provider registered", caps.provider_name == "mock"))
    results.append(_ok("C mock supports pitch/energy/rhythm", caps.supports_pitch and caps.supports_energy and caps.supports_rhythm))
    return results


async def check_mock_runtime() -> list[bool]:
    results: list[bool] = []
    wav = _make_tone_wav()
    prov = build_prosody_provider("mock")
    raw, evidence, flags, used = await analyze_prosody_audio(wav, provider=prov, generated_at=NOW)
    results.append(_ok("D canonical ProsodyFeatureEvidence returned", evidence is not None))
    results.append(_ok("E mock provenance", evidence.provenance.provider_name == "mock"))
    results.append(_ok("F prosody validation passes", not validate_prosody_evidence(evidence)))
    results.append(_ok("G expression observations present", len(list(raw.get("expression_observations") or [])) > 0))
    results.append(_ok("H deterministic mock processing_version", str(raw.get("processing_version")) == "s6_mock"))
    mapped, _ = provider_dict_to_prosody_evidence(raw, generated_at=NOW)
    results.append(_ok("I provider dict maps to S3 evidence", mapped.provenance.provider_name == evidence.provenance.provider_name))
    return results


def check_provider_registration() -> list[bool]:
    from app.services.language_speaking_providers.prosody_hume import HumeProsodyProvider

    from app.services.language_speaking_providers.prosody_acoustic import AcousticProsodyProvider

    results: list[bool] = []
    settings = get_settings()
    results.append(_ok("J acoustic + hume registered", {"acoustic", "hume"} <= supported_prosody_providers()))
    results.append(_ok("K production default acoustic", (settings.SPEAKING_PROSODY_PROVIDER or "").strip().lower() == "acoustic"))
    results.append(_ok("L real provider name acoustic", AcousticProsodyProvider().capabilities().provider_name == "acoustic"))
    results.append(_ok("L2 hume provider still real class", HumeProsodyProvider().capabilities().provider_name == "hume"))

    try:
        build_prosody_provider("whisperx")
        results.append(_ok("M no silent fallback unknown provider", False))
    except ProsodyProviderUnavailableError:
        results.append(_ok("M no silent fallback unknown provider", True))

    # Acoustic provider needs no API key and must build as the real default.
    prov = build_prosody_provider("acoustic")
    results.append(_ok("N acoustic provider builds (no key needed)", prov.capabilities().provider_name == "acoustic"))
    return results


def check_derived_acoustic() -> list[bool]:
    results: list[bool] = []
    wav = _make_tone_wav(seconds=1.5)
    derived = derive_acoustic_prosody(wav)
    signals = list(derived.get("signal_observations") or [])
    tags = {str(s.get("signal_tag")) for s in signals if isinstance(s, dict)}
    results.append(_ok("O derived pause signals", "pause_count" in tags))
    results.append(_ok("P derived pitch signals", "pitch_std_hz" in tags))
    results.append(_ok("Q derived energy signals", "energy_std" in tags))
    unavailable = list(derived.get("unavailable_evidence") or [])
    results.append(_ok("R word-aligned pauses unavailable", "word_aligned_pauses_unavailable" in unavailable))
    sources = {str(s.get("source")) for s in signals if isinstance(s, dict)}
    results.append(_ok("S derived signals tagged derived_acoustic", "derived_acoustic" in sources))
    return results


def check_expression_mapping() -> list[bool]:
    results: list[bool] = []
    tag = normalize_expression_label("Anxiety")
    results.append(_ok("T expression mapping stable tag", tag == "expression:anxiety"))
    return results


async def check_orchestrator() -> list[bool]:
    results: list[bool] = []
    wav = _make_tone_wav()
    art = _artifact(wav)

    prosody_result = await process_speaking_prosody(art, wav, provider_name="mock", now=NOW)
    results.append(_ok("U orchestrator success", prosody_result.success))
    if prosody_result.prosody:
        results.append(_ok("V facts result has provenance", prosody_result.prosody.provenance.provider_name == "mock"))
        edu = validate_no_educational_fields_in_dict(prosody_result.prosody.to_persistence_dict())
        results.append(_ok("W no educational fields", not edu, ",".join(edu)))
    if prosody_result.bundle:
        results.append(_ok("X bundle prosody populated", prosody_result.bundle.availability_for(SpeakingEvidenceFamily.prosody)))

    # Preserve transcript + phoneme from prior bundle
    pron = await process_speaking_pronunciation(
        art,
        wav,
        expected_task_text="hello",
        provider_name="mock",
        now=NOW,
    )
    stacked = await process_speaking_prosody(
        art,
        wav,
        existing_bundle=pron.bundle,
        provider_name="mock",
        now=NOW,
    )
    if stacked.bundle:
        results.append(
            _ok(
                "Y preserves phoneme_alignment slot",
                stacked.bundle.availability_for(SpeakingEvidenceFamily.phoneme_alignment),
            )
        )
        results.append(_ok("Z prosody slot added alongside phoneme", stacked.bundle.availability_for(SpeakingEvidenceFamily.prosody)))
    else:
        results.extend([_ok("Y preserves phoneme_alignment slot", False), _ok("Z prosody slot added alongside phoneme", False)])

    serialized = json.dumps(prosody_result.prosody.to_persistence_dict() if prosody_result.prosody else {}, sort_keys=True)
    serialized2 = json.dumps(prosody_result.prosody.to_persistence_dict() if prosody_result.prosody else {}, sort_keys=True)
    results.append(_ok("AA deterministic serialization", serialized == serialized2))
    return results


def check_taxonomy_and_sources() -> list[bool]:
    results: list[bool] = []
    results.append(
        _ok(
            "AB issue tags stable prefix",
            all(t.startswith(("prosody:", "delivery:")) for t in ALL_PROSODY_ISSUE_TAGS),
        )
    )
    results.append(
        _ok(
            "AC ownership edge evaluation_runtime->prosody",
            "language_speaking_prosody" in ALLOWED_PACKAGE_DEPENDENCIES.get("language_speaking_evaluation_runtime", frozenset()),
        )
    )
    results.append(_ok("AD ProsodyEvidenceSource enum", ProsodyEvidenceSource.direct_provider.value == "direct_provider"))
    return results


def check_isolation() -> list[bool]:
    results: list[bool] = []
    forbidden_hits: list[str] = []
    scan_roots = [
        SERVICES / "language_speaking_prosody",
        SERVICES / "language_speaking_evaluation_runtime" / "prosody_runtime.py",
    ]
    forbidden_tokens = (
        "official_speaking_cefr",
        "learning_stage_speaking",
        "promotion_readiness_score",
        "apply_observation",
        "update_mastery",
        "pass_fail",
        "mastery_level",
    )
    for root in scan_roots:
        paths = [root] if root.is_file() else list(root.glob("**/*.py"))
        for py in paths:
            text = py.read_text(encoding="utf-8").lower()
            for tok in forbidden_tokens:
                if tok in text:
                    forbidden_hits.append(f"{py.name}:{tok}")
    results.append(_ok("AE no S2/CEFR/stage/readiness writes in S6", not forbidden_hits, ",".join(forbidden_hits)))
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
        ("S5", "scripts/verify_speaking_s5_pronunciation.py"),
    ]
    for label, script in scripts:
        path = BACKEND / script
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            timeout=600,
        )
        results.append(_ok(f"{label} verification remains green", proc.returncode == 0))
    return results


async def async_main() -> int:
    print("Speaking S6 Prosody Runtime Verification\n")
    if not _resolve_ffmpeg():
        print("WARN: ffmpeg not available — some checks may be limited")

    sections: list[tuple[str, object]] = [
        ("Capability discovery (A-C)", check_capability_discovery),
        ("Mock runtime (D-I)", check_mock_runtime),
        ("Provider registration (J-N)", check_provider_registration),
        ("Derived acoustic (O-S)", check_derived_acoustic),
        ("Expression mapping (T)", check_expression_mapping),
        ("Orchestrator (U-AA)", check_orchestrator),
        ("Taxonomy/sources (AB-AD)", check_taxonomy_and_sources),
        ("Isolation (AE)", check_isolation),
        ("Frozen layers S0-S5", check_frozen_layers),
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
        print("S6 STRUCTURAL -- READY for real Hume verification.")
        return 0
    print("S6 NOT READY -- fix failures.")
    return 1


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
