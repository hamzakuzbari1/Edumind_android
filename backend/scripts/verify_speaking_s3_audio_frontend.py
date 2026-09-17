"""Verify Speaking S3 Audio Frontend contracts.

Usage (from backend/):
    python scripts/verify_speaking_s3_audio_frontend.py

Architecture/contracts only — no provider SDKs, no educational scoring.
"""

from __future__ import annotations

import ast
import importlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
APP = BACKEND / "app"
SERVICES = APP / "services"

from app.services.language_speaking.enums import SpeakingAudioSource  # noqa: E402
from app.services.language_speaking.ownership import (  # noqa: E402
    ALLOWED_PACKAGE_DEPENDENCIES,
    FORBIDDEN_PROVIDER_SDK_IMPORTS,
    PACKAGE_OWNERSHIP,
    REQUIRED_S0_PACKAGES,
)
from app.services.language_speaking.types import PauseMarker, WordTiming  # noqa: E402
from app.services.language_speaking_audio_frontend.artifacts import (  # noqa: E402
    AudioArtifactKind,
    NormalizedAudioArtifact,
    SpeakingAudioArtifact,
)
from app.services.language_speaking_audio_frontend.bundle import (  # noqa: E402
    assemble_evidence_bundle,
)
from app.services.language_speaking_audio_frontend.capabilities import (  # noqa: E402
    ProviderCapabilityDescriptor,
    compute_evidence_availability,
)
from app.services.language_speaking_audio_frontend.enums import (  # noqa: E402
    AudioEvidenceQualityFlag,
    ProviderCapabilityFlag,
    SpeakingEvidenceFamily,
)
from app.services.language_speaking_audio_frontend.evidence import (  # noqa: E402
    EmbeddingFrameMetadata,
    EnergySummary,
    PhonemeAlignmentEntry,
    PhonemeAlignmentEvidence,
    PitchSummary,
    ProviderProvenance,
    ProsodyFeatureEvidence,
    SpeakingRateEvidence,
    SpeechEmbeddingEvidence,
    TranscriptEvidence,
    TranscriptSegment,
)
from app.services.language_speaking_audio_frontend.legacy_mapping import (  # noqa: E402
    AUDIO_RETENTION_BOUNDARIES,
    LEGACY_AUDIO_CONTRACT_MAP,
    LEGACY_STORAGE_FIELD_MAP,
    LEGACY_TRANSCRIPTION_FIELD_MAP,
)
from app.services.language_speaking_audio_frontend.validators import (  # noqa: E402
    FORBIDDEN_EDUCATIONAL_FIELD_NAMES,
    quality_flags_from_partial_availability,
    validate_embedding_metadata,
    validate_no_educational_fields_in_dict,
    validate_phoneme_alignment_evidence,
    validate_phoneme_alignment_timestamps,
    validate_prosody_evidence,
    validate_segment_timestamps_ordered,
    validate_transcript_evidence,
    validate_word_timestamps_ordered,
)
from app.services.language_speaking_audio_session.enums import SpeakingAudioLifecycleState  # noqa: E402
from app.services.language_speaking_audio_session.transitions import (  # noqa: E402
    IllegalAudioSessionTransition,
    LEGAL_AUDIO_SESSION_TRANSITIONS,
    is_legal_transition,
)
from app.services.language_speaking_audio_session.types import SpeakingAudioSessionRecord  # noqa: E402

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def _sample_raw_artifact() -> SpeakingAudioArtifact:
    return SpeakingAudioArtifact(
        audio_id="audio_s3_qa_001",
        session_id="session_s3_qa_001",
        student_id=5,
        language_id=1,
        source_type=SpeakingAudioSource.browser_recording,
        original_filename="recording.webm",
        content_type="audio/webm",
        codec="opus",
        container_format="webm",
        sample_rate_hz=48_000,
        channel_count=1,
        duration_ms=3200,
        byte_size=48_000,
        storage_reference="/uploads/student_5/language_conversation/recording.webm",
        captured_at=NOW,
    )


def _sample_transcript(*, with_words: bool = False) -> TranscriptEvidence:
    words = ()
    if with_words:
        words = (
            WordTiming("hello", 0.0, 0.4, 0.95),
            WordTiming("world", 0.5, 0.9, 0.92),
        )
    return TranscriptEvidence(
        text="hello world",
        language="en",
        provider_confidence=0.93,
        words=words,
        segments=(TranscriptSegment("hello world", 0.0, 0.9, 0.93),),
        provenance=ProviderProvenance(
            provider_name="whisperx",
            model_name="large-v3",
            provider_version="3.1.1",
            processing_version="s3_contract",
            generated_at=NOW,
            evidence_family=SpeakingEvidenceFamily.transcript,
        ),
    )


def check_raw_audio_artifact() -> list[bool]:
    results: list[bool] = []
    art = _sample_raw_artifact()
    results.append(_ok("canonical raw audio artifact creation", art.audio_id == "audio_s3_qa_001"))
    results.append(_ok("raw artifact has storage_reference not bytes", bool(art.storage_reference)))
    results.append(_ok("raw artifact kind is raw", art.artifact_kind == AudioArtifactKind.raw))
    d = art.to_persistence_dict()
    results.append(_ok("raw artifact roundtrip fields", d["audio_id"] == art.audio_id and d["student_id"] == 5))
    results.append(_ok("SpeakingAudioInput alias", SpeakingAudioArtifact is not None))
    from app.services.language_speaking_audio_frontend.artifacts import SpeakingAudioInput  # noqa: WPS433

    results.append(_ok("SpeakingAudioInput is SpeakingAudioArtifact", SpeakingAudioInput is SpeakingAudioArtifact))
    return results


def check_normalized_artifact() -> list[bool]:
    results: list[bool] = []
    raw = _sample_raw_artifact()
    norm = NormalizedAudioArtifact(
        audio_id="audio_s3_norm_001",
        session_id=raw.session_id,
        student_id=raw.student_id,
        language_id=raw.language_id,
        source_audio_id=raw.audio_id,
        storage_reference="/uploads/student_5/language_conversation/recording_norm.wav",
        duration_ms=raw.duration_ms,
        byte_size=64_000,
        normalized_at=NOW,
    )
    results.append(_ok("normalized artifact distinct from raw", norm.artifact_kind == AudioArtifactKind.normalized))
    results.append(_ok("normalized traces source_audio_id", norm.source_audio_id == raw.audio_id))
    results.append(_ok("normalized canonical sample rate", norm.sample_rate_hz == 16_000))
    results.append(_ok("normalized mono channel", norm.channel_count == 1))
    results.append(_ok("raw and normalized have different audio_id", norm.audio_id != raw.audio_id))
    return results


def check_session_lifecycle() -> list[bool]:
    results: list[bool] = []
    rec = SpeakingAudioSessionRecord(
        session_id="session_s3_qa_001",
        student_id=5,
        language_id=1,
        audio_source=SpeakingAudioSource.browser_recording,
        lifecycle_state=SpeakingAudioLifecycleState.created,
        created_at=NOW,
    )
    legal_pairs = [
        (SpeakingAudioLifecycleState.created, SpeakingAudioLifecycleState.uploading),
        (SpeakingAudioLifecycleState.uploading, SpeakingAudioLifecycleState.uploaded),
        (SpeakingAudioLifecycleState.uploaded, SpeakingAudioLifecycleState.normalizing),
        (SpeakingAudioLifecycleState.normalizing, SpeakingAudioLifecycleState.ready),
        (SpeakingAudioLifecycleState.ready, SpeakingAudioLifecycleState.processing),
        (SpeakingAudioLifecycleState.processing, SpeakingAudioLifecycleState.processed),
        (SpeakingAudioLifecycleState.processed, SpeakingAudioLifecycleState.expired),
    ]
    for frm, to in legal_pairs:
        results.append(_ok(f"legal transition {frm.value} -> {to.value}", is_legal_transition(frm, to)))

    illegal_pairs = [
        (SpeakingAudioLifecycleState.created, SpeakingAudioLifecycleState.ready),
        (SpeakingAudioLifecycleState.processed, SpeakingAudioLifecycleState.processing),
        (SpeakingAudioLifecycleState.failed, SpeakingAudioLifecycleState.ready),
        (SpeakingAudioLifecycleState.expired, SpeakingAudioLifecycleState.created),
    ]
    for frm, to in illegal_pairs:
        results.append(_ok(f"illegal transition rejected {frm.value} -> {to.value}", not is_legal_transition(frm, to)))

    moved = rec.with_transition(SpeakingAudioLifecycleState.uploading, now=NOW)
    results.append(_ok("with_transition applies legal move", moved.lifecycle_state == SpeakingAudioLifecycleState.uploading))
    try:
        rec.with_transition(SpeakingAudioLifecycleState.ready)
        results.append(_ok("with_transition raises on illegal move", False))
    except IllegalAudioSessionTransition:
        results.append(_ok("with_transition raises on illegal move", True))

    results.append(_ok("all lifecycle states in transition map", len(LEGAL_AUDIO_SESSION_TRANSITIONS) == 9))
    return results


def check_transcript_evidence() -> list[bool]:
    results: list[bool] = []
    tx = _sample_transcript(with_words=True)
    results.append(_ok("transcript evidence roundtrip text", tx.text == "hello world"))
    d = tx.to_persistence_dict()
    results.append(_ok("transcript persistence dict", d["text"] == "hello world" and d["language"] == "en"))
    results.append(_ok("transcript validate passes", not validate_transcript_evidence(tx)))

    good_words = (WordTiming("a", 0.0, 0.2), WordTiming("b", 0.3, 0.5))
    results.append(_ok("word timestamp ordering valid", not validate_word_timestamps_ordered(good_words)))
    bad_words = (WordTiming("b", 0.5, 0.7), WordTiming("a", 0.1, 0.3))
    results.append(_ok("word timestamp ordering invalid detected", bool(validate_word_timestamps_ordered(bad_words))))

    good_segs = (TranscriptSegment("a", 0.0, 0.5), TranscriptSegment("b", 0.6, 1.0))
    results.append(_ok("segment timestamp ordering valid", not validate_segment_timestamps_ordered(good_segs)))
    bad_segs = (TranscriptSegment("b", 0.6, 1.0), TranscriptSegment("a", 0.0, 0.5))
    results.append(_ok("segment timestamp ordering invalid detected", bool(validate_segment_timestamps_ordered(bad_segs))))
    return results


def check_embedding_evidence() -> list[bool]:
    results: list[bool] = []
    emb = SpeechEmbeddingEvidence(
        embedding_reference="embed/store/wavlm_001",
        model_identifier="wavlm-base-plus",
        embedding_dimension=768,
        frame_metadata=EmbeddingFrameMetadata(frame_count=120, window_size_ms=20, hop_size_ms=10, sample_rate_hz=16000),
        provenance=ProviderProvenance(provider_name="wavlm", model_name="base-plus", evidence_family=SpeakingEvidenceFamily.speech_embedding),
    )
    results.append(_ok("embedding metadata validation passes", not validate_embedding_metadata(emb)))
    results.append(_ok("embedding dimension validation", emb.embedding_dimension == 768))
    bad = SpeechEmbeddingEvidence(embedding_reference="", model_identifier="", embedding_dimension=0)
    results.append(_ok("embedding validation catches bad metadata", bool(validate_embedding_metadata(bad))))
    d = emb.to_persistence_dict()
    results.append(_ok("embedding no raw tensor in persistence", "embedding_reference" in d and "tensor" not in d))
    return results


def check_phoneme_evidence() -> list[bool]:
    results: list[bool] = []
    alignments = (
        PhonemeAlignmentEntry("θ", "θ", 0.0, 0.1, 0.95, "think", "θɪŋk", 0),
        PhonemeAlignmentEntry("ɪ", "ɪ", 0.1, 0.2, 0.90, "think", "θɪŋk", 1),
    )
    ph = PhonemeAlignmentEvidence(
        alignments=alignments,
        provenance=ProviderProvenance(provider_name="speechbrain", evidence_family=SpeakingEvidenceFamily.phoneme_alignment),
    )
    results.append(_ok("phoneme alignment timestamp validation passes", not validate_phoneme_alignment_timestamps(alignments)))
    results.append(_ok("phoneme alignment evidence validates", not validate_phoneme_alignment_evidence(ph)))
    bad = (PhonemeAlignmentEntry("a", "b", 0.5, 0.2, position=0),)
    results.append(_ok("phoneme bad timestamps detected", bool(validate_phoneme_alignment_timestamps(bad))))
    return results


def check_prosody_evidence() -> list[bool]:
    results: list[bool] = []
    pro = ProsodyFeatureEvidence(
        pitch=PitchSummary(mean_hz=180.0, std_hz=25.0, range_hz=80.0),
        energy=EnergySummary(mean=0.65, std=0.12),
        speaking_rate=SpeakingRateEvidence(words_per_minute=120.0),
        provenance=ProviderProvenance(provider_name="opensmile", evidence_family=SpeakingEvidenceFamily.prosody),
    )
    results.append(_ok("prosody evidence validation passes", not validate_prosody_evidence(pro)))
    d = pro.to_persistence_dict()
    results.append(_ok("prosody persistence has pitch/energy/rate", "pitch" in d and "energy" in d))
    return results


def check_missing_capabilities() -> list[bool]:
    results: list[bool] = []
    tx_only = ProviderCapabilityDescriptor(
        provider_name="whisper",
        capabilities=frozenset({ProviderCapabilityFlag.transcription}),
    )
    avail = compute_evidence_availability((tx_only,))
    results.append(_ok("transcript-only: transcript available", avail[SpeakingEvidenceFamily.transcript]))
    results.append(_ok("transcript-only: phoneme NOT available", not avail[SpeakingEvidenceFamily.phoneme_alignment]))
    results.append(_ok("transcript-only: prosody NOT available", not avail[SpeakingEvidenceFamily.prosody]))
    results.append(_ok("transcript-only: embedding NOT available", not avail[SpeakingEvidenceFamily.speech_embedding]))

    bundle = assemble_evidence_bundle(
        evidence_bundle_id="bundle_partial",
        session_id="session_s3_qa_001",
        audio_id="audio_s3_qa_001",
        transcript=_sample_transcript(),
    )
    results.append(_ok("missing phoneme explicit in bundle", not bundle.availability_for(SpeakingEvidenceFamily.phoneme_alignment)))
    results.append(_ok("missing prosody explicit in bundle", not bundle.availability_for(SpeakingEvidenceFamily.prosody)))
    results.append(_ok("no fake phoneme evidence", bundle.phoneme_alignment is None))
    results.append(_ok("no fake prosody evidence", bundle.prosody is None))
    return results


def check_provenance() -> list[bool]:
    results: list[bool] = []
    p1 = ProviderProvenance(provider_name="whisperx", model_name="large-v3", provider_version="3.1.1", generated_at=NOW, evidence_family=SpeakingEvidenceFamily.transcript)
    p2 = ProviderProvenance(provider_name="wavlm", model_name="base-plus", evidence_family=SpeakingEvidenceFamily.speech_embedding)
    bundle = assemble_evidence_bundle(
        evidence_bundle_id="bundle_prov",
        session_id="session_s3_qa_001",
        audio_id="audio_s3_qa_001",
        transcript=_sample_transcript(),
        speech_embedding=SpeechEmbeddingEvidence(
            embedding_reference="embed/001",
            model_identifier="wavlm-base",
            embedding_dimension=768,
            provenance=p2,
        ),
        provider_provenance=(p1, p2),
    )
    results.append(_ok("provider provenance preserved", len(bundle.provider_provenance) >= 2))
    names = {p.provider_name for p in bundle.provider_provenance}
    results.append(_ok("multiple provider provenance supported", "whisperx" in names or "wavlm" in names))
    return results


def check_quality_warnings() -> list[bool]:
    results: list[bool] = []
    avail = {
        "transcript": True,
        "phoneme_alignment": False,
        "prosody": False,
        "speech_embedding": False,
    }
    flags = quality_flags_from_partial_availability(avail)
    results.append(_ok("quality flags from partial availability", AudioEvidenceQualityFlag.alignment_unavailable in flags))
    results.append(_ok("prosody unavailable flag", AudioEvidenceQualityFlag.prosody_unavailable in flags))

    bundle = assemble_evidence_bundle(
        evidence_bundle_id="bundle_warn",
        session_id="session_s3_qa_001",
        audio_id="audio_s3_qa_001",
        transcript=_sample_transcript(),
        quality_flags=(AudioEvidenceQualityFlag.partial_processing, AudioEvidenceQualityFlag.alignment_unavailable),
        processing_warnings=("phoneme provider not configured",),
    )
    results.append(_ok("quality warnings preserved in bundle", len(bundle.quality_flags) == 2))
    results.append(_ok("processing warnings preserved", len(bundle.processing_warnings) == 1))
    return results


def check_bundle_serialization() -> list[bool]:
    results: list[bool] = []
    bundle = assemble_evidence_bundle(
        evidence_bundle_id="bundle_det",
        session_id="session_s3_qa_001",
        audio_id="audio_s3_qa_001",
        transcript=_sample_transcript(with_words=True),
        assembled_at=NOW,
    )
    j1 = bundle.to_deterministic_json()
    j2 = bundle.to_deterministic_json()
    results.append(_ok("evidence bundle deterministic serialization", j1 == j2))
    parsed = json.loads(j1)
    results.append(_ok("schema version present", parsed.get("schema_version") == "0.3.0"))
    results.append(_ok("evidence availability map present", "evidence_availability" in parsed))
    forbidden = validate_no_educational_fields_in_dict(parsed)
    results.append(_ok("no forbidden educational fields in bundle", not forbidden, str(forbidden[:3])))
    return results


def check_no_educational_judgement() -> list[bool]:
    results: list[bool] = []
    bundle = assemble_evidence_bundle(
        evidence_bundle_id="bundle_no_edu",
        session_id="session_s3_qa_001",
        audio_id="audio_s3_qa_001",
        transcript=_sample_transcript(),
    )
    d = bundle.to_persistence_dict()
    for forbidden in ("pass", "fail", "mastery", "readiness", "promotion", "lesson_completed", "cefr"):
        results.append(_ok(f"no {forbidden} field in bundle", forbidden not in d))
    results.append(_ok("FORBIDDEN_EDUCATIONAL_FIELD_NAMES defined", len(FORBIDDEN_EDUCATIONAL_FIELD_NAMES) >= 10))
    return results


def check_capability_compositions() -> list[bool]:
    results: list[bool] = []

    # A. Transcript-only
    desc_a = ProviderCapabilityDescriptor("whisper", frozenset({ProviderCapabilityFlag.transcription}))
    avail_a = compute_evidence_availability((desc_a,))
    bundle_a = assemble_evidence_bundle(
        evidence_bundle_id="comp_a",
        session_id="s1",
        audio_id="a1",
        transcript=_sample_transcript(),
    )
    results.append(_ok("composition A: transcript-only available", avail_a[SpeakingEvidenceFamily.transcript]))
    results.append(_ok("composition A: bundle has transcript only", bundle_a.transcript is not None and bundle_a.phoneme_alignment is None))

    # B. Transcript + timestamps
    desc_b = ProviderCapabilityDescriptor(
        "whisperx",
        frozenset({ProviderCapabilityFlag.transcription, ProviderCapabilityFlag.word_timestamps, ProviderCapabilityFlag.segment_timestamps}),
    )
    avail_b = compute_evidence_availability((desc_b,))
    tx_b = _sample_transcript(with_words=True)
    results.append(_ok("composition B: transcript+timestamps available", avail_b[SpeakingEvidenceFamily.transcript]))
    results.append(_ok("composition B: words present", len(tx_b.words) == 2))

    # C. Transcript + phoneme alignment
    desc_c = ProviderCapabilityDescriptor(
        "whisperx",
        frozenset({ProviderCapabilityFlag.transcription, ProviderCapabilityFlag.phoneme_alignment}),
    )
    avail_c = compute_evidence_availability((desc_c,))
    bundle_c = assemble_evidence_bundle(
        evidence_bundle_id="comp_c",
        session_id="s1",
        audio_id="a1",
        transcript=_sample_transcript(),
        phoneme_alignment=PhonemeAlignmentEvidence(
            alignments=(PhonemeAlignmentEntry("θ", "θ", 0.0, 0.1),),
        ),
    )
    results.append(_ok("composition C: phoneme available", avail_c[SpeakingEvidenceFamily.phoneme_alignment]))
    results.append(_ok("composition C: bundle has phoneme", bundle_c.phoneme_alignment is not None))

    # D. Transcript + embeddings + prosody
    bundle_d = assemble_evidence_bundle(
        evidence_bundle_id="comp_d",
        session_id="s1",
        audio_id="a1",
        transcript=_sample_transcript(),
        speech_embedding=SpeechEmbeddingEvidence("embed/d", "hubert", 768),
        prosody=ProsodyFeatureEvidence(pitch=PitchSummary(mean_hz=200.0)),
    )
    results.append(_ok("composition D: all three families present", all([bundle_d.transcript, bundle_d.speech_embedding, bundle_d.prosody])))

    # E. Full composed from multiple providers
    desc_e1 = ProviderCapabilityDescriptor("whisperx", frozenset({ProviderCapabilityFlag.transcription, ProviderCapabilityFlag.word_timestamps, ProviderCapabilityFlag.phoneme_alignment}))
    desc_e2 = ProviderCapabilityDescriptor("wavlm", frozenset({ProviderCapabilityFlag.speech_embeddings}))
    desc_e3 = ProviderCapabilityDescriptor("opensmile", frozenset({ProviderCapabilityFlag.pitch, ProviderCapabilityFlag.energy, ProviderCapabilityFlag.pauses}))
    avail_e = compute_evidence_availability((desc_e1, desc_e2, desc_e3))
    results.append(_ok("composition E: all families available", all(avail_e.values())))

    # F. Partial processing with warnings
    bundle_f = assemble_evidence_bundle(
        evidence_bundle_id="comp_f",
        session_id="s1",
        audio_id="a1",
        transcript=_sample_transcript(),
        quality_flags=(AudioEvidenceQualityFlag.partial_processing, AudioEvidenceQualityFlag.prosody_unavailable),
        processing_warnings=("prosody provider timeout",),
    )
    results.append(_ok("composition F: partial with warnings", AudioEvidenceQualityFlag.prosody_unavailable in bundle_f.quality_flags))
    results.append(_ok("composition F: prosody not faked", bundle_f.prosody is None))
    return results


def check_isolation() -> list[bool]:
    results: list[bool] = []
    educational_packages = [
        "language_speaking_knowledge_model",
        "language_speaking_evaluator",
        "language_speaking_coach",
        "language_speaking_pronunciation",
        "language_speaking_fluency",
        "language_speaking_prosody",
        "language_speaking_progression",
    ]
    forbidden_imports = (
        "language_speaking_audio_frontend",
        "language_speaking_providers",
    )
    for pkg in educational_packages:
        pkg_dir = SERVICES / pkg
        if not pkg_dir.is_dir():
            continue
        for py_file in pkg_dir.glob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for imp in forbidden_imports:
                if f"app.services.{imp}" in text:
                    results.append(_ok(f"no {imp} in {pkg}/{py_file.name}", False))
            for sdk in FORBIDDEN_PROVIDER_SDK_IMPORTS:
                if sdk in text.lower():
                    results.append(_ok(f"no SDK '{sdk}' in {pkg}/{py_file.name}", False))

    # Explicit S2 import scan
    km_dir = SERVICES / "language_speaking_knowledge_model"
    km_imports: set[str] = set()
    for py_file in km_dir.glob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "audio_frontend" in node.module or "language_speaking_providers" in node.module:
                    km_imports.add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "audio_frontend" in alias.name or "language_speaking_providers" in alias.name:
                        km_imports.add(alias.name)
    results.append(_ok("S2 knowledge model does not import audio frontend/providers", not km_imports, str(km_imports)))
    return results


def check_legacy_mapping() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("legacy audio contract map documented", len(LEGACY_AUDIO_CONTRACT_MAP) >= 8))
    results.append(_ok("legacy transcription field map", "text" in LEGACY_TRANSCRIPTION_FIELD_MAP))
    results.append(_ok("legacy storage field map", "storage_key" in LEGACY_STORAGE_FIELD_MAP))
    results.append(_ok("retention boundaries documented", len(AUDIO_RETENTION_BOUNDARIES) >= 5))
    results.append(_ok("raw audio retention boundary", "raw_audio" in AUDIO_RETENTION_BOUNDARIES))
    results.append(_ok("embeddings retention boundary", "embeddings" in AUDIO_RETENTION_BOUNDARIES))

    arch = SERVICES / "language_speaking_audio_frontend" / "AUDIO_FRONTEND_ARCHITECTURE.md"
    if arch.is_file():
        text = arch.read_text(encoding="utf-8")
        results.append(_ok("AUDIO_FRONTEND_ARCHITECTURE.md exists", True))
        results.append(_ok("architecture doc: retention", "Retention" in text))
        results.append(_ok("architecture doc: legacy boundary", "Legacy boundary" in text))
        results.append(_ok("architecture doc: S4 readiness", "S4 readiness" in text))
    else:
        results.append(_ok("AUDIO_FRONTEND_ARCHITECTURE.md exists", False))
    return results


def check_ownership_dag() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("audio_frontend in ownership registry", "language_speaking_audio_frontend" in PACKAGE_OWNERSHIP))
    results.append(_ok("audio_session in ownership registry", "language_speaking_audio_session" in PACKAGE_OWNERSHIP))
    af_deps = ALLOWED_PACKAGE_DEPENDENCIES.get("language_speaking_audio_frontend", frozenset())
    results.append(_ok("audio_frontend deps limited to providers", af_deps == frozenset({"language_speaking_providers"})))
    as_deps = ALLOWED_PACKAGE_DEPENDENCIES.get("language_speaking_audio_session", frozenset())
    results.append(_ok("audio_session has no speaking deps", len(as_deps) == 0))
    return results


def check_frozen_layers() -> list[bool]:
    results: list[bool] = []
    scripts = [
        ("S0", "scripts/verify_speaking_s0_architecture.py"),
        ("S1", "scripts/verify_speaking_s1_skill_graph.py"),
        ("S2", "scripts/verify_speaking_s2_knowledge_model.py"),
        ("S2 DB", "scripts/verify_speaking_s2_persistence_db.py"),
    ]
    for label, script in scripts:
        path = BACKEND / script
        if not path.is_file():
            results.append(_ok(f"{label} verification script exists", False))
            continue
        try:
            proc = subprocess.run(
                [sys.executable, str(path)],
                cwd=str(BACKEND),
                capture_output=True,
                text=True,
                timeout=120,
            )
            passed = proc.returncode == 0
            detail = "" if passed else (proc.stdout.splitlines()[-1] if proc.stdout else proc.stderr[:200])
            results.append(_ok(f"{label} verification remains green", passed, detail))
        except subprocess.TimeoutExpired:
            results.append(_ok(f"{label} verification remains green", False, "timeout"))
    return results


def check_contract_importability() -> list[bool]:
    results: list[bool] = []
    contracts = [
        ("SpeakingAudioArtifact", "app.services.language_speaking_audio_frontend.artifacts"),
        ("NormalizedAudioArtifact", "app.services.language_speaking_audio_frontend.artifacts"),
        ("SpeakingAudioEvidenceBundle", "app.services.language_speaking_audio_frontend.bundle"),
        ("TranscriptEvidence", "app.services.language_speaking_audio_frontend.evidence"),
        ("SpeechEmbeddingEvidence", "app.services.language_speaking_audio_frontend.evidence"),
        ("PhonemeAlignmentEvidence", "app.services.language_speaking_audio_frontend.evidence"),
        ("ProsodyFeatureEvidence", "app.services.language_speaking_audio_frontend.evidence"),
        ("ProviderCapabilityDescriptor", "app.services.language_speaking_audio_frontend.capabilities"),
        ("SpeakingAudioSessionRecord", "app.services.language_speaking_audio_session.types"),
        ("SpeakingAudioLifecycleState", "app.services.language_speaking_audio_session.enums"),
    ]
    for name, mod_path in contracts:
        mod = importlib.import_module(mod_path)
        results.append(_ok(f"contract importable: {name}", hasattr(mod, name)))
    return results


def main() -> int:
    print("Speaking S3 Audio Frontend Verification\n")
    sections = [
        ("Raw audio artifact", check_raw_audio_artifact),
        ("Normalized artifact", check_normalized_artifact),
        ("Session lifecycle", check_session_lifecycle),
        ("Transcript evidence", check_transcript_evidence),
        ("Embedding evidence", check_embedding_evidence),
        ("Phoneme alignment evidence", check_phoneme_evidence),
        ("Prosody evidence", check_prosody_evidence),
        ("Missing capabilities explicit", check_missing_capabilities),
        ("Provider provenance", check_provenance),
        ("Quality warnings", check_quality_warnings),
        ("Bundle serialization", check_bundle_serialization),
        ("No educational judgement", check_no_educational_judgement),
        ("Capability compositions A-F", check_capability_compositions),
        ("Isolation (no SDK in educational packages)", check_isolation),
        ("Legacy mapping", check_legacy_mapping),
        ("Ownership DAG", check_ownership_dag),
        ("Contract importability", check_contract_importability),
        ("Frozen layers (S0/S1/S2/S2-DB)", check_frozen_layers),
    ]

    all_results: list[bool] = []
    for title, fn in sections:
        print(f"[{title}]")
        all_results.extend(fn())
        print()

    passed = sum(all_results)
    total = len(all_results)
    print(f"Summary: {passed}/{total} checks passed")
    if passed == total:
        print("S3 READY -- S4 may begin after review.")
        print("STOP -- do not start S4.")
        return 0
    print("S3 NOT READY -- fix failures before S4.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
