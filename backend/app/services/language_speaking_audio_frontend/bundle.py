"""SpeakingAudioEvidenceBundle assembly (S3).

One provider-neutral bundle consumed by future S4–S7 analysis engines.
Missing provider capability is explicit — never faked.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.services.language_speaking_audio_frontend.enums import (
    AudioEvidenceQualityFlag,
    SpeakingEvidenceFamily,
)
from app.services.language_speaking_audio_frontend.evidence import (
    LANGUAGE_SPEAKING_EVIDENCE_SCHEMA_VERSION,
    PhonemeAlignmentEvidence,
    ProviderProvenance,
    ProsodyFeatureEvidence,
    SpeechEmbeddingEvidence,
    TranscriptEvidence,
)

LANGUAGE_SPEAKING_EVIDENCE_BUNDLE_VERSION = "0.3.0"


@dataclass(frozen=True, slots=True)
class SpeakingAudioEvidenceBundle:
    """Canonical bundle of all audio evidence families for one audio clip.

    Downstream educational engines consume this object — never raw provider
    responses or raw audio bytes. Missing families are None with explicit
    availability flags.
    """

    evidence_bundle_id: str
    session_id: str
    audio_id: str
    transcript: TranscriptEvidence | None = None
    speech_embedding: SpeechEmbeddingEvidence | None = None
    phoneme_alignment: PhonemeAlignmentEvidence | None = None
    prosody: ProsodyFeatureEvidence | None = None
    provider_provenance: tuple[ProviderProvenance, ...] = ()
    processing_warnings: tuple[str, ...] = ()
    quality_flags: tuple[AudioEvidenceQualityFlag, ...] = ()
    evidence_availability: dict[str, bool] = field(default_factory=dict)
    assembled_at: datetime | None = None
    schema_version: str = LANGUAGE_SPEAKING_EVIDENCE_BUNDLE_VERSION

    def availability_for(self, family: SpeakingEvidenceFamily) -> bool:
        """Return explicit availability for one evidence family."""
        return self.evidence_availability.get(family.value, False)

    def to_persistence_dict(self) -> dict[str, object]:
        """Deterministic JSON-serializable representation."""
        return {
            "evidence_bundle_id": self.evidence_bundle_id,
            "session_id": self.session_id,
            "audio_id": self.audio_id,
            "transcript": self.transcript.to_persistence_dict() if self.transcript else None,
            "speech_embedding": self.speech_embedding.to_persistence_dict() if self.speech_embedding else None,
            "phoneme_alignment": self.phoneme_alignment.to_persistence_dict() if self.phoneme_alignment else None,
            "prosody": self.prosody.to_persistence_dict() if self.prosody else None,
            "provider_provenance": [p.to_persistence_dict() for p in self.provider_provenance],
            "processing_warnings": list(self.processing_warnings),
            "quality_flags": [f.value for f in self.quality_flags],
            "evidence_availability": dict(sorted(self.evidence_availability.items())),
            "assembled_at": self.assembled_at.isoformat() if self.assembled_at else None,
            "schema_version": self.schema_version,
        }

    def to_deterministic_json(self) -> str:
        """Return a deterministic JSON string for roundtrip verification."""
        return json.dumps(self.to_persistence_dict(), sort_keys=True, separators=(",", ":"))


def assemble_evidence_bundle(
    *,
    evidence_bundle_id: str,
    session_id: str,
    audio_id: str,
    transcript: TranscriptEvidence | None = None,
    speech_embedding: SpeechEmbeddingEvidence | None = None,
    phoneme_alignment: PhonemeAlignmentEvidence | None = None,
    prosody: ProsodyFeatureEvidence | None = None,
    provider_provenance: tuple[ProviderProvenance, ...] = (),
    processing_warnings: tuple[str, ...] = (),
    quality_flags: tuple[AudioEvidenceQualityFlag, ...] = (),
    assembled_at: datetime | None = None,
) -> SpeakingAudioEvidenceBundle:
    """Assemble a bundle with explicit availability — never fakes missing evidence.

    If a family is None, its availability flag is False. If a family is present,
    its availability flag is True. This prevents silent fake evidence.
    """
    availability: dict[str, bool] = {
        SpeakingEvidenceFamily.transcript.value: transcript is not None,
        SpeakingEvidenceFamily.speech_embedding.value: speech_embedding is not None,
        SpeakingEvidenceFamily.phoneme_alignment.value: phoneme_alignment is not None,
        SpeakingEvidenceFamily.prosody.value: prosody is not None,
    }

    # Collect provenance from individual evidence objects if not supplied.
    provenance_list = list(provider_provenance)
    for ev in (transcript, speech_embedding, phoneme_alignment, prosody):
        if ev is not None and ev.provenance is not None:
            if ev.provenance not in provenance_list:
                provenance_list.append(ev.provenance)

    return SpeakingAudioEvidenceBundle(
        evidence_bundle_id=evidence_bundle_id,
        session_id=session_id,
        audio_id=audio_id,
        transcript=transcript,
        speech_embedding=speech_embedding,
        phoneme_alignment=phoneme_alignment,
        prosody=prosody,
        provider_provenance=tuple(provenance_list),
        processing_warnings=processing_warnings,
        quality_flags=quality_flags,
        evidence_availability=availability,
        assembled_at=assembled_at,
    )


def bundle_from_persistence_dict(raw: dict[str, Any]) -> SpeakingAudioEvidenceBundle:
    """Reconstruct a bundle from a persistence dict (for roundtrip tests)."""
    # Minimal reconstruction for verification — full deserialization in S4+.
    return SpeakingAudioEvidenceBundle(
        evidence_bundle_id=str(raw.get("evidence_bundle_id", "")),
        session_id=str(raw.get("session_id", "")),
        audio_id=str(raw.get("audio_id", "")),
        transcript=None if raw.get("transcript") is None else _stub_transcript(raw["transcript"]),
        speech_embedding=None if raw.get("speech_embedding") is None else _stub_embedding(raw["speech_embedding"]),
        phoneme_alignment=None if raw.get("phoneme_alignment") is None else _stub_phoneme(raw["phoneme_alignment"]),
        prosody=None if raw.get("prosody") is None else _stub_prosody(raw["prosody"]),
        provider_provenance=(),
        processing_warnings=tuple(raw.get("processing_warnings") or []),
        quality_flags=tuple(
            AudioEvidenceQualityFlag(v) for v in (raw.get("quality_flags") or [])
        ),
        evidence_availability=dict(raw.get("evidence_availability") or {}),
        schema_version=str(raw.get("schema_version", LANGUAGE_SPEAKING_EVIDENCE_BUNDLE_VERSION)),
    )


def _stub_transcript(raw: dict[str, Any]) -> TranscriptEvidence:
    return TranscriptEvidence(
        text=str(raw.get("text", "")),
        language=str(raw.get("language", "en")),
        provider_confidence=float(raw.get("provider_confidence", 0.0)),
        evidence_version=str(raw.get("evidence_version", LANGUAGE_SPEAKING_EVIDENCE_SCHEMA_VERSION)),
    )


def _stub_embedding(raw: dict[str, Any]) -> SpeechEmbeddingEvidence:
    return SpeechEmbeddingEvidence(
        embedding_reference=str(raw.get("embedding_reference", "")),
        model_identifier=str(raw.get("model_identifier", "")),
        embedding_dimension=int(raw.get("embedding_dimension", 0)),
        evidence_version=str(raw.get("evidence_version", LANGUAGE_SPEAKING_EVIDENCE_SCHEMA_VERSION)),
    )


def _stub_phoneme(raw: dict[str, Any]) -> PhonemeAlignmentEvidence:
    return PhonemeAlignmentEvidence(
        alignments=(),
        evidence_version=str(raw.get("evidence_version", LANGUAGE_SPEAKING_EVIDENCE_SCHEMA_VERSION)),
    )


def _stub_prosody(raw: dict[str, Any]) -> ProsodyFeatureEvidence:
    return ProsodyFeatureEvidence(
        evidence_version=str(raw.get("evidence_version", LANGUAGE_SPEAKING_EVIDENCE_SCHEMA_VERSION)),
    )
