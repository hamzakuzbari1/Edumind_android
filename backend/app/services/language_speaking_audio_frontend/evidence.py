"""Provider-neutral audio evidence family contracts (S3).

These are observations/evidence only. They MUST NOT contain pass/fail, mastery,
readiness, CEFR promotion, or lesson-completion decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.services.language_speaking.types import PauseMarker, WordTiming
from app.services.language_speaking_audio_frontend.enums import SpeakingEvidenceFamily

LANGUAGE_SPEAKING_EVIDENCE_SCHEMA_VERSION = "0.3.0"


@dataclass(frozen=True, slots=True)
class ProviderProvenance:
    """Provenance for one provider contribution to an evidence family."""

    provider_name: str
    model_name: str = ""
    provider_version: str = ""
    processing_version: str = ""
    generated_at: datetime | None = None
    evidence_family: SpeakingEvidenceFamily | None = None

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "provider_version": self.provider_version,
            "processing_version": self.processing_version,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "evidence_family": self.evidence_family.value if self.evidence_family else None,
        }


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """One transcript segment with optional timestamps."""

    text: str
    start_sec: float
    end_sec: float
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class TranscriptEvidence:
    """Canonical transcript evidence — text and timing facts only."""

    text: str
    language: str
    provider_confidence: float
    segments: tuple[TranscriptSegment, ...] = ()
    words: tuple[WordTiming, ...] = ()
    detected_pauses: tuple[PauseMarker, ...] = ()
    provenance: ProviderProvenance | None = None
    evidence_version: str = LANGUAGE_SPEAKING_EVIDENCE_SCHEMA_VERSION

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "language": self.language,
            "provider_confidence": round(self.provider_confidence, 4),
            "segments": [
                {
                    "text": s.text,
                    "start_sec": s.start_sec,
                    "end_sec": s.end_sec,
                    "confidence": s.confidence,
                }
                for s in self.segments
            ],
            "words": [
                {"word": w.word, "start_sec": w.start_sec, "end_sec": w.end_sec, "confidence": w.confidence}
                for w in self.words
            ],
            "detected_pauses": [
                {
                    "start_sec": p.start_sec,
                    "end_sec": p.end_sec,
                    "duration_sec": p.duration_sec,
                    "placement": p.placement,
                }
                for p in self.detected_pauses
            ],
            "provenance": self.provenance.to_persistence_dict() if self.provenance else None,
            "evidence_version": self.evidence_version,
        }


@dataclass(frozen=True, slots=True)
class EmbeddingFrameMetadata:
    """Frame/window metadata for a speech embedding — no raw tensor."""

    frame_count: int = 0
    window_size_ms: int = 0
    hop_size_ms: int = 0
    sample_rate_hz: int = 0


@dataclass(frozen=True, slots=True)
class SpeechEmbeddingEvidence:
    """Canonical speech embedding evidence — opaque reference only.

    Raw provider tensors MUST NOT appear in downstream educational objects.
    """

    embedding_reference: str
    model_identifier: str
    embedding_dimension: int
    frame_metadata: EmbeddingFrameMetadata = field(default_factory=EmbeddingFrameMetadata)
    provenance: ProviderProvenance | None = None
    evidence_version: str = LANGUAGE_SPEAKING_EVIDENCE_SCHEMA_VERSION

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "embedding_reference": self.embedding_reference,
            "model_identifier": self.model_identifier,
            "embedding_dimension": self.embedding_dimension,
            "frame_metadata": {
                "frame_count": self.frame_metadata.frame_count,
                "window_size_ms": self.frame_metadata.window_size_ms,
                "hop_size_ms": self.frame_metadata.hop_size_ms,
                "sample_rate_hz": self.frame_metadata.sample_rate_hz,
            },
            "provenance": self.provenance.to_persistence_dict() if self.provenance else None,
            "evidence_version": self.evidence_version,
        }


@dataclass(frozen=True, slots=True)
class PhonemeAlignmentEntry:
    """One phoneme alignment observation — evidence only, not pass/fail."""

    expected_phoneme: str
    observed_phoneme: str
    start_sec: float
    end_sec: float
    alignment_confidence: float = 0.0
    word_reference: str = ""
    syllable_reference: str = ""
    position: int = 0


@dataclass(frozen=True, slots=True)
class PhonemeAlignmentEvidence:
    """Canonical phoneme alignment evidence."""

    alignments: tuple[PhonemeAlignmentEntry, ...]
    provenance: ProviderProvenance | None = None
    evidence_version: str = LANGUAGE_SPEAKING_EVIDENCE_SCHEMA_VERSION

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "alignments": [
                {
                    "expected_phoneme": a.expected_phoneme,
                    "observed_phoneme": a.observed_phoneme,
                    "start_sec": a.start_sec,
                    "end_sec": a.end_sec,
                    "alignment_confidence": a.alignment_confidence,
                    "word_reference": a.word_reference,
                    "syllable_reference": a.syllable_reference,
                    "position": a.position,
                }
                for a in self.alignments
            ],
            "provenance": self.provenance.to_persistence_dict() if self.provenance else None,
            "evidence_version": self.evidence_version,
        }


@dataclass(frozen=True, slots=True)
class PitchSummary:
    mean_hz: float = 0.0
    std_hz: float = 0.0
    range_hz: float = 0.0
    min_hz: float = 0.0
    max_hz: float = 0.0


@dataclass(frozen=True, slots=True)
class EnergySummary:
    mean: float = 0.0
    std: float = 0.0
    peak: float = 0.0


@dataclass(frozen=True, slots=True)
class SpeakingRateEvidence:
    words_per_minute: float = 0.0
    syllables_per_minute: float = 0.0
    articulation_rate_wpm: float = 0.0


@dataclass(frozen=True, slots=True)
class PauseEvidence:
    pauses: tuple[PauseMarker, ...] = ()
    total_pause_duration_sec: float = 0.0
    pause_count: int = 0


@dataclass(frozen=True, slots=True)
class RhythmEvidence:
    regularity: float = 0.0
    nPVI: float = 0.0  # normalized pairwise variability index (if available)


@dataclass(frozen=True, slots=True)
class StressEvidence:
    stressed_syllable_count: int = 0
    stress_accuracy_ratio: float | None = None  # evidence ratio, not pass/fail


@dataclass(frozen=True, slots=True)
class IntonationEvidence:
    phrase_final_rise: bool | None = None
    contour_type: str = ""


@dataclass(frozen=True, slots=True)
class ProsodyFeatureEvidence:
    """Canonical prosody/acoustic evidence — language learning only."""

    pitch: PitchSummary = field(default_factory=PitchSummary)
    energy: EnergySummary = field(default_factory=EnergySummary)
    speaking_rate: SpeakingRateEvidence = field(default_factory=SpeakingRateEvidence)
    pause: PauseEvidence = field(default_factory=PauseEvidence)
    rhythm: RhythmEvidence = field(default_factory=RhythmEvidence)
    stress: StressEvidence = field(default_factory=StressEvidence)
    intonation: IntonationEvidence = field(default_factory=IntonationEvidence)
    provenance: ProviderProvenance | None = None
    evidence_version: str = LANGUAGE_SPEAKING_EVIDENCE_SCHEMA_VERSION

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "pitch": {
                "mean_hz": self.pitch.mean_hz,
                "std_hz": self.pitch.std_hz,
                "range_hz": self.pitch.range_hz,
                "min_hz": self.pitch.min_hz,
                "max_hz": self.pitch.max_hz,
            },
            "energy": {
                "mean": self.energy.mean,
                "std": self.energy.std,
                "peak": self.energy.peak,
            },
            "speaking_rate": {
                "words_per_minute": self.speaking_rate.words_per_minute,
                "syllables_per_minute": self.speaking_rate.syllables_per_minute,
                "articulation_rate_wpm": self.speaking_rate.articulation_rate_wpm,
            },
            "pause": {
                "pauses": [
                    {
                        "start_sec": p.start_sec,
                        "end_sec": p.end_sec,
                        "duration_sec": p.duration_sec,
                        "placement": p.placement,
                    }
                    for p in self.pause.pauses
                ],
                "total_pause_duration_sec": self.pause.total_pause_duration_sec,
                "pause_count": self.pause.pause_count,
            },
            "rhythm": {
                "regularity": self.rhythm.regularity,
                "nPVI": self.rhythm.nPVI,
            },
            "stress": {
                "stressed_syllable_count": self.stress.stressed_syllable_count,
                "stress_accuracy_ratio": self.stress.stress_accuracy_ratio,
            },
            "intonation": {
                "phrase_final_rise": self.intonation.phrase_final_rise,
                "contour_type": self.intonation.contour_type,
            },
            "provenance": self.provenance.to_persistence_dict() if self.provenance else None,
            "evidence_version": self.evidence_version,
        }
