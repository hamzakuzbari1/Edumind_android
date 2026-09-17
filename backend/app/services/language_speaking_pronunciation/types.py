"""Canonical pronunciation evidence types (S5).

Facts-only contract: no pass/fail, mastery, CEFR, readiness, stage, or grades.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

LANGUAGE_SPEAKING_PRONUNCIATION_VERSION = "0.5.0"
LANGUAGE_SPEAKING_PRONUNCIATION_SCHEMA_VERSION = "0.5.0"


class PronunciationReferenceSource(StrEnum):
    """How the lexical reference for pronunciation alignment was chosen."""

    expected_task_text = "expected_task_text"
    transcript_hypothesis = "transcript_hypothesis"


class PhonemeAlignmentOperation(StrEnum):
    """Alignment operation between expected and observed phonemes."""

    match = "match"
    substitution = "substitution"
    omission = "omission"
    insertion = "insertion"


@dataclass(frozen=True, slots=True)
class PronunciationProvenance:
    """Provider provenance for pronunciation analysis."""

    provider_name: str
    model_name: str = ""
    provider_version: str = ""
    processing_version: str = ""
    reference_source: PronunciationReferenceSource | None = None

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "provider_version": self.provider_version,
            "processing_version": self.processing_version,
            "reference_source": self.reference_source.value if self.reference_source else None,
        }


@dataclass(frozen=True, slots=True)
class PhonemeObservation:
    """One phoneme-level pronunciation observation — evidence only."""

    expected_phoneme: str
    observed_phoneme: str
    start_sec: float
    end_sec: float
    alignment_confidence: float = 0.0
    operation: PhonemeAlignmentOperation = PhonemeAlignmentOperation.match
    word_reference: str = ""
    position: int = 0


@dataclass(frozen=True, slots=True)
class WordPronunciationObservation:
    """Word-level pronunciation evidence derived from acoustic alignment."""

    word: str
    start_sec: float
    end_sec: float
    expected_phonemes: tuple[str, ...] = ()
    observed_phonemes: tuple[str, ...] = ()
    phoneme_observations: tuple[PhonemeObservation, ...] = ()
    word_confidence: float = 0.0
    issue_tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PronunciationIssueObservation:
    """Stable pronunciation issue tag with optional deterministic skill mapping."""

    issue_tag: str
    word_reference: str = ""
    expected_phoneme: str = ""
    observed_phoneme: str = ""
    candidate_skill_ids: tuple[str, ...] = ()
    evidence_reliability: float = 0.0


@dataclass(frozen=True, slots=True)
class SpeakingPronunciationEvidenceResult:
    """Canonical S5 pronunciation evidence result — facts only."""

    audio_id: str
    session_id: str
    reference_source: PronunciationReferenceSource
    reference_text: str
    provenance: PronunciationProvenance
    analyzed_words: tuple[WordPronunciationObservation, ...] = ()
    phoneme_observations: tuple[PhonemeObservation, ...] = ()
    issue_observations: tuple[PronunciationIssueObservation, ...] = ()
    evidence_coverage: float = 0.0
    evidence_reliability: float = 0.0
    unavailable_evidence: tuple[str, ...] = ()
    processing_warnings: tuple[str, ...] = ()
    schema_version: str = LANGUAGE_SPEAKING_PRONUNCIATION_SCHEMA_VERSION

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "audio_id": self.audio_id,
            "session_id": self.session_id,
            "reference_source": self.reference_source.value,
            "reference_text": self.reference_text,
            "provenance": self.provenance.to_persistence_dict(),
            "analyzed_words": [
                {
                    "word": w.word,
                    "start_sec": w.start_sec,
                    "end_sec": w.end_sec,
                    "expected_phonemes": list(w.expected_phonemes),
                    "observed_phonemes": list(w.observed_phonemes),
                    "word_confidence": w.word_confidence,
                    "issue_tags": list(w.issue_tags),
                }
                for w in self.analyzed_words
            ],
            "phoneme_observations": [
                {
                    "expected_phoneme": p.expected_phoneme,
                    "observed_phoneme": p.observed_phoneme,
                    "start_sec": p.start_sec,
                    "end_sec": p.end_sec,
                    "alignment_confidence": p.alignment_confidence,
                    "operation": p.operation.value,
                    "word_reference": p.word_reference,
                    "position": p.position,
                }
                for p in self.phoneme_observations
            ],
            "issue_observations": [
                {
                    "issue_tag": i.issue_tag,
                    "word_reference": i.word_reference,
                    "expected_phoneme": i.expected_phoneme,
                    "observed_phoneme": i.observed_phoneme,
                    "candidate_skill_ids": list(i.candidate_skill_ids),
                    "evidence_reliability": i.evidence_reliability,
                }
                for i in self.issue_observations
            ],
            "evidence_coverage": self.evidence_coverage,
            "evidence_reliability": self.evidence_reliability,
            "unavailable_evidence": list(self.unavailable_evidence),
            "processing_warnings": list(self.processing_warnings),
            "schema_version": self.schema_version,
        }


# Backward-compatible alias for S0 verifier references.
PronunciationAnalysisFacts = SpeakingPronunciationEvidenceResult
