"""Canonical prosody/delivery evidence types (S6).

Facts-only contract: no pass/fail, mastery, CEFR, readiness, stage, or grades.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

LANGUAGE_SPEAKING_PROSODY_VERSION = "0.6.0"
LANGUAGE_SPEAKING_PROSODY_SCHEMA_VERSION = "0.6.0"


class ProsodyEvidenceSource(StrEnum):
    """How a prosody signal was obtained."""

    direct_provider = "direct_provider"
    derived_acoustic = "derived_acoustic"
    unavailable = "unavailable"


@dataclass(frozen=True, slots=True)
class ProsodyProvenance:
    """Provider provenance for prosody analysis."""

    provider_name: str
    model_name: str = ""
    provider_version: str = ""
    processing_version: str = ""

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "provider_version": self.provider_version,
            "processing_version": self.processing_version,
        }


@dataclass(frozen=True, slots=True)
class ExpressionObservation:
    """Hume expression dimension mapped to stable canonical tag."""

    provider_label: str
    normalized_tag: str
    confidence: float
    source: ProsodyEvidenceSource = ProsodyEvidenceSource.direct_provider
    segment_start_sec: float = 0.0
    segment_end_sec: float = 0.0


@dataclass(frozen=True, slots=True)
class ProsodySignalObservation:
    """One measurable prosody/delivery signal."""

    signal_tag: str
    value: float
    source: ProsodyEvidenceSource
    reliability: float = 0.0


@dataclass(frozen=True, slots=True)
class ProsodyIssueObservation:
    """Stable prosody/delivery issue tag with optional skill mapping."""

    issue_tag: str
    candidate_skill_ids: tuple[str, ...] = ()
    evidence_reliability: float = 0.0
    source: ProsodyEvidenceSource = ProsodyEvidenceSource.derived_acoustic


@dataclass(frozen=True, slots=True)
class TurnSegmentObservation:
    """Timed segment from provider (turn/utterance boundary)."""

    start_sec: float
    end_sec: float
    speaker_id: str = ""


@dataclass(frozen=True, slots=True)
class SpeakingProsodyEvidenceResult:
    """Canonical S6 prosody evidence result — facts only."""

    audio_id: str
    session_id: str
    source_audio_id: str
    provenance: ProsodyProvenance
    expression_observations: tuple[ExpressionObservation, ...] = ()
    signal_observations: tuple[ProsodySignalObservation, ...] = ()
    issue_observations: tuple[ProsodyIssueObservation, ...] = ()
    turn_segments: tuple[TurnSegmentObservation, ...] = ()
    candidate_skill_ids: tuple[str, ...] = ()
    evidence_coverage: float = 0.0
    evidence_reliability: float = 0.0
    unavailable_evidence: tuple[str, ...] = ()
    quality_flags: tuple[str, ...] = ()
    processing_warnings: tuple[str, ...] = ()
    schema_version: str = LANGUAGE_SPEAKING_PROSODY_SCHEMA_VERSION

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "audio_id": self.audio_id,
            "session_id": self.session_id,
            "source_audio_id": self.source_audio_id,
            "provenance": self.provenance.to_persistence_dict(),
            "expression_observations": [
                {
                    "provider_label": e.provider_label,
                    "normalized_tag": e.normalized_tag,
                    "confidence": e.confidence,
                    "source": e.source.value,
                    "segment_start_sec": e.segment_start_sec,
                    "segment_end_sec": e.segment_end_sec,
                }
                for e in self.expression_observations
            ],
            "signal_observations": [
                {
                    "signal_tag": s.signal_tag,
                    "value": s.value,
                    "source": s.source.value,
                    "reliability": s.reliability,
                }
                for s in self.signal_observations
            ],
            "issue_observations": [
                {
                    "issue_tag": i.issue_tag,
                    "candidate_skill_ids": list(i.candidate_skill_ids),
                    "evidence_reliability": i.evidence_reliability,
                    "source": i.source.value,
                }
                for i in self.issue_observations
            ],
            "turn_segments": [
                {"start_sec": t.start_sec, "end_sec": t.end_sec, "speaker_id": t.speaker_id}
                for t in self.turn_segments
            ],
            "candidate_skill_ids": list(self.candidate_skill_ids),
            "evidence_coverage": self.evidence_coverage,
            "evidence_reliability": self.evidence_reliability,
            "unavailable_evidence": list(self.unavailable_evidence),
            "quality_flags": list(self.quality_flags),
            "processing_warnings": list(self.processing_warnings),
            "schema_version": self.schema_version,
        }


# Backward-compatible alias for S0 verifier references.
ProsodyAnalysisFacts = SpeakingProsodyEvidenceResult
