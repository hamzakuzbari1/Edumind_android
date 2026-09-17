"""Real S6 prosody acceptance verifier (derived-acoustic production path).

Context: Hume's Expression Measurement (prosody) API was discontinued by the
vendor on 2026-06-14 and returns HTTP 403. The S6 production evidence path is
therefore the numpy-derived acoustic provider computed directly from the real
normalized WAV. This verifier proves REAL derived prosody evidence on a real
human recording — no external API, no mock, no silent fallback.

Usage (from backend/):
    set SPEAKING_S6_HUMAN_AUDIO_FIXTURE=C:\\path\\to\\human_speech.(wav|ogg|mp3|m4a)
    python scripts/verify_speaking_s6_real_hume.py

ACCEPTANCE: FAIL (exit 1), not SKIP, when the real provider path or real
evidence cannot be produced.
"""

from __future__ import annotations

import asyncio
import io
import os
import subprocess
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.services.language_speaking.enums import SpeakingAudioSource  # noqa: E402
from app.services.language_speaking_audio_frontend.bundle import assemble_evidence_bundle  # noqa: E402
from app.services.language_speaking_audio_frontend.enums import SpeakingEvidenceFamily  # noqa: E402
from app.services.language_speaking_audio_frontend.errors import (  # noqa: E402
    ProsodyProviderDiscontinuedError,
    ProsodyProviderUnavailableError,
    SpeakingAudioRuntimeError,
)
from app.services.language_speaking_audio_frontend.evidence import (  # noqa: E402
    PhonemeAlignmentEntry,
    PhonemeAlignmentEvidence,
    ProviderProvenance,
    TranscriptEvidence,
)
from app.services.language_speaking_audio_frontend.media_adapter import artifact_from_bytes  # noqa: E402
from app.services.language_speaking_audio_frontend.normalization_runtime import (  # noqa: E402
    _resolve_ffmpeg,
    normalize_audio_with_bytes,
)
from app.services.language_speaking_audio_frontend.prosody_factory import (  # noqa: E402
    build_prosody_provider,
    supported_prosody_providers,
)
from app.services.language_speaking_audio_frontend.prosody_runtime import analyze_prosody_audio  # noqa: E402
from app.services.language_speaking_audio_frontend.validators import (  # noqa: E402
    validate_no_educational_fields_in_dict,
)
from app.services.language_speaking_evaluation_runtime.prosody_runtime import process_speaking_prosody  # noqa: E402
from app.services.language_speaking_prosody.types import ProsodyEvidenceSource  # noqa: E402

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
_SUPPORTED_INPUT_SUFFIXES = frozenset(
    {".wav", ".mp3", ".ogg", ".opus", ".m4a", ".webm", ".flac", ".aac", ".mp4", ".mkv"}
)


def _ok(label: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    line = f"  [{mark}] {label}"
    if detail:
        line += f" -- {detail}"
    print(line)
    return passed


def _content_type_for(path: Path) -> str:
    return {
        ".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg",
        ".opus": "audio/opus", ".m4a": "audio/mp4", ".mp4": "audio/mp4",
        ".webm": "audio/webm", ".flac": "audio/flac", ".aac": "audio/mp4",
    }.get(path.suffix.lower(), "audio/ogg")


def _artifact_from_file(audio_path: Path) -> tuple[object, bytes]:
    data = audio_path.read_bytes()
    art = artifact_from_bytes(
        audio_id="audio_s6_real",
        session_id="session_s6_real",
        student_id=6,
        language_id=1,
        audio_bytes=data,
        original_filename=audio_path.name,
        content_type=_content_type_for(audio_path),
        audio_source=SpeakingAudioSource.file_upload,
        captured_at=NOW,
    )
    return art, data


def _ffprobe_format(audio_path: Path) -> str:
    ffmpeg = _resolve_ffmpeg()
    if not ffmpeg:
        return audio_path.suffix.lstrip(".").upper()
    probe = ffmpeg.replace("ffmpeg", "ffprobe")
    try:
        result = subprocess.run(
            [probe, "-v", "error", "-show_entries", "format=format_name,duration",
             "-of", "default=noprint_wrappers=1", str(audio_path)],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().replace("\n", ", ")
    except Exception:
        pass
    return audio_path.suffix.lstrip(".").upper()


async def main_async() -> int:
    print("=" * 72)
    print("Speaking S6 - REAL PROSODY ACCEPTANCE (derived-acoustic production path)")
    print("Note: Hume Expression Measurement API discontinued 2026-06-14 (HTTP 403).")
    print("=" * 72)
    settings = get_settings()
    results: list[bool] = []

    if not _resolve_ffmpeg():
        print("  [FAIL] ffmpeg required for normalization.")
        return 1

    human_fixture = os.environ.get("SPEAKING_S6_HUMAN_AUDIO_FIXTURE", "").strip()
    if not human_fixture or not Path(human_fixture).is_file():
        print("  [FAIL] SPEAKING_S6_HUMAN_AUDIO_FIXTURE must point to a real human recording.")
        print(f"         Got: {human_fixture!r}")
        return 1

    audio_path = Path(human_fixture)
    if audio_path.suffix.lower() not in _SUPPORTED_INPUT_SUFFIXES:
        print(f"  [FAIL] Unsupported audio format: {audio_path.suffix}")
        return 1
    print(f"\nHUMAN AUDIO FIXTURE: {audio_path}")

    # ---- [1-4] Real provider / real computation / no mock / no silent fallback ----
    print("\n[1-4] Provider selection / real computation / no mock / no silent fallback")
    provider_default = (settings.SPEAKING_PROSODY_PROVIDER or "").strip().lower()
    results.append(_ok("1 real production provider default is acoustic", provider_default == "acoustic", provider_default))
    try:
        provider = build_prosody_provider()  # uses configured default
    except ProsodyProviderUnavailableError as exc:
        print(f"  [FAIL] provider unavailable: {exc}")
        return 1
    results.append(_ok("1b real acoustic provider selected", provider.capabilities().provider_name == "acoustic"))
    results.append(_ok("3 no mock provider used", type(provider).__name__ == "AcousticProsodyProvider"))

    art, data = _artifact_from_file(audio_path)
    normalized, wav_bytes, _ = normalize_audio_with_bytes(art, data, now=NOW)

    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        norm_sr = wf.getframerate()
        norm_ch = wf.getnchannels()
        norm_dur = wf.getnframes() / norm_sr if norm_sr else 0.0
    source_format = _ffprobe_format(audio_path)

    raw, evidence, flags, used = await analyze_prosody_audio(wav_bytes, provider=provider, generated_at=NOW)
    results.append(_ok("2 real derivation ran on real WAV (dict response)", isinstance(raw, dict)))
    results.append(_ok("2b response came from acoustic provider", str(raw.get("provider_name")) == "acoustic"))
    results.append(_ok("4 no silent fallback (provider stayed acoustic)", used.capabilities().provider_name == "acoustic"))

    print("\n[Orchestrator] process_speaking_prosody() with real acoustic provider")
    runtime = await process_speaking_prosody(art, data, now=NOW)
    results.append(_ok("orchestrator completed", runtime.success, runtime.error.code if runtime.error else ""))
    if not runtime.success:
        print("\nS6 REAL ACCEPTANCE -- FAILED")
        return 1
    prosody = runtime.prosody
    bundle = runtime.bundle

    # ---- [5] Provenance ----
    print("\n[5] PROVIDER PROVENANCE")
    prov = prosody.provenance
    print(f"    provider_name      : {prov.provider_name}")
    print(f"    model_name         : {prov.model_name}")
    print(f"    provider_version   : {prov.provider_version}")
    print(f"    processing_version : {prov.processing_version}")
    results.append(_ok("5 provenance provider_name=acoustic", prov.provider_name == "acoustic"))
    results.append(_ok("5b provenance model recorded", bool(prov.model_name)))

    # ---- [6-7] Real derived prosody signals + values ----
    print("\n[6-7] REAL DERIVED PROSODY SIGNALS + VALUES (from the human recording)")
    signals = list(prosody.signal_observations)
    for s in signals:
        print(f"    {s.signal_tag:<26} value={s.value:.4f}  reliability={s.reliability:.2f}  source={s.source.value}")
    tags = {s.signal_tag for s in signals}
    core_present = bool({"pitch_std_hz", "energy_std", "pause_count"} & tags)
    results.append(_ok("6 real prosody signals returned", len(signals) > 0))
    results.append(_ok("6b core pitch/energy/pause signals present", core_present, ",".join(sorted(tags))))
    results.append(_ok("7 numeric values + reliabilities present", all(s.reliability >= 0 for s in signals) and len(signals) > 0))

    # ---- [8] Direct provider evidence (this provider = acoustic derivation) ----
    print("\n[8] DIRECT PROVIDER EVIDENCE (acoustic provider output)")
    print(f"    provider signal observations : {len(signals)}")
    print(f"    provider expression labels   : {len(prosody.expression_observations)} (expression model not available)")
    results.append(_ok("8 direct provider evidence present", len(signals) > 0))

    # ---- [9] Derived acoustic evidence, separated ----
    print("\n[9] DERIVED ACOUSTIC EVIDENCE (tagged derived_acoustic)")
    derived_signals = [s for s in signals if s.source == ProsodyEvidenceSource.derived_acoustic]
    print(f"    derived_acoustic signals: {len(derived_signals)} / {len(signals)}")
    results.append(_ok("9 derived acoustic evidence present + tagged", len(derived_signals) > 0))
    results.append(_ok("9b all signals from real derivation", len(derived_signals) == len(signals)))

    # ---- [10] Unavailable evidence, explicit ----
    print("\n[10] UNAVAILABLE EVIDENCE (explicit - never faked)")
    for u in prosody.unavailable_evidence:
        print(f"    unavailable: {u}")
    results.append(_ok("10a word-aligned pauses explicitly unavailable", "word_aligned_pauses_unavailable" in prosody.unavailable_evidence))
    results.append(_ok("10b expression evidence explicitly unavailable", "expression_evidence_unavailable" in prosody.unavailable_evidence))

    # ---- [11] bundle.prosody populated ----
    print("\n[11-13] BUNDLE POPULATION + PRESERVATION")
    results.append(_ok("11 bundle.prosody populated", bundle is not None and bundle.availability_for(SpeakingEvidenceFamily.prosody)))

    # ---- [12-13] transcript + S5 phoneme preserved on stacking ----
    existing_transcript = TranscriptEvidence(
        text="technology helps students learn languages",
        language="en",
        provider_confidence=0.95,
        provenance=ProviderProvenance(provider_name="openai", model_name="gpt-4o-transcribe",
                                      evidence_family=SpeakingEvidenceFamily.transcript),
    )
    existing_phoneme = PhonemeAlignmentEvidence(
        alignments=(
            PhonemeAlignmentEntry(expected_phoneme="t", observed_phoneme="t", start_sec=0.0, end_sec=0.1,
                                  alignment_confidence=0.9, word_reference="technology", position=0),
        ),
        provenance=ProviderProvenance(provider_name="wav2vec2", model_name="facebook/wav2vec2-lv-60-espeak-cv-ft",
                                      evidence_family=SpeakingEvidenceFamily.phoneme_alignment),
    )
    prior_bundle = assemble_evidence_bundle(
        evidence_bundle_id="bundle_stack_test",
        session_id="session_s6_real",
        audio_id="audio_s6_real",
        transcript=existing_transcript,
        phoneme_alignment=existing_phoneme,
        assembled_at=NOW,
    )
    stacked = await process_speaking_prosody(art, data, existing_bundle=prior_bundle, now=NOW)
    sb = stacked.bundle
    transcript_preserved = bool(sb and sb.transcript is not None and sb.transcript.text == existing_transcript.text)
    phoneme_preserved = bool(sb and sb.phoneme_alignment is not None and len(sb.phoneme_alignment.alignments) == 1)
    prosody_added = bool(sb and sb.availability_for(SpeakingEvidenceFamily.prosody))
    print(f"    transcript preserved : {transcript_preserved}")
    print(f"    phoneme preserved    : {phoneme_preserved}")
    print(f"    prosody added        : {prosody_added}")
    results.append(_ok("12 transcript evidence preserved when stacking", transcript_preserved))
    results.append(_ok("13 S5 phoneme evidence preserved when stacking", phoneme_preserved))
    results.append(_ok("13b prosody added alongside transcript+phoneme", prosody_added))

    # ---- [14] No mastery/CEFR/stage/readiness/progression ----
    print("\n[14] NO EDUCATIONAL/MASTERY/CEFR/STAGE/READINESS/PROGRESSION FIELDS")
    edu = validate_no_educational_fields_in_dict(prosody.to_persistence_dict())
    edu_bundle = validate_no_educational_fields_in_dict(bundle.to_persistence_dict())
    results.append(_ok("14 no forbidden fields in prosody result", not edu, ",".join(edu)))
    results.append(_ok("14b no forbidden fields in bundle", not edu_bundle, ",".join(edu_bundle)))

    # ---- [15] Structured errors: unknown provider + discontinued Hume ----
    print("\n[15] STRUCTURED ERROR HANDLING (no silent fallback, no raw leak)")
    unknown_structured = False
    try:
        build_prosody_provider("whisperx")
    except ProsodyProviderUnavailableError:
        unknown_structured = True
    except Exception:
        unknown_structured = False
    results.append(_ok("15a unknown provider -> structured error", unknown_structured))

    # Prove the discontinued Hume path maps to a structured discontinued error
    # (only if a key is present to actually reach the API).
    hume_key = (settings.HUME_API_KEY or "").strip()
    if hume_key and "hume" in supported_prosody_providers():
        discontinued_structured = False
        err_name = ""
        try:
            hume_provider = build_prosody_provider("hume")
            await analyze_prosody_audio(wav_bytes, provider=hume_provider, generated_at=NOW)
            err_name = "NO ERROR"
        except ProsodyProviderDiscontinuedError as exc:
            discontinued_structured = True
            err_name = f"ProsodyProviderDiscontinuedError({exc.code})"
        except SpeakingAudioRuntimeError as exc:
            discontinued_structured = True
            err_name = f"{type(exc).__name__}({exc.code})"
        except Exception as exc:
            discontinued_structured = False
            err_name = f"RAW {type(exc).__name__}"
        print(f"    discontinued Hume result: {err_name}")
        results.append(_ok("15b discontinued Hume -> structured error (no raw leak)", discontinued_structured, err_name))
    else:
        print("    (Hume key absent — skipping live discontinued-path probe)")

    # ---- [16] Exact audio duration + format ----
    print("\n[16] AUDIO DURATION + FORMAT")
    print(f"    source file     : {audio_path.name}")
    print(f"    source format   : {source_format}")
    print(f"    source bytes    : {len(data)}")
    print(f"    normalized      : {norm_sr} Hz, {norm_ch} channel(s), PCM16 WAV")
    print(f"    duration        : {norm_dur:.2f} s")
    results.append(_ok("16 exact duration + format reported", norm_dur > 0.0 and norm_sr == 16000 and norm_ch == 1))

    passed = sum(results)
    total = len(results)
    print("\n" + "=" * 72)
    print(f"Summary: {passed}/{total} checks passed")
    if passed == total:
        print("S6 REAL ACCEPTANCE (derived-acoustic) -- PASSED")
        print("=" * 72)
        return 0
    print("S6 REAL ACCEPTANCE -- FAILED")
    print("=" * 72)
    return 1


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
