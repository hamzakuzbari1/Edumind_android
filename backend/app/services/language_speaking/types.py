"""Canonical Speaking core types (S0 stubs) — session and speech evidence contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.services.language_speaking.enums import (
    SpeakingAudioSource,
    SpeakingConversationState,
    SpeakingSessionProcessingState,
)

SPEAKING_CORE_TYPES_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class WordTiming:
    """One word with start/end timestamps (seconds from clip start)."""

    word: str
    start_sec: float
    end_sec: float
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class PhonemeAlignment:
    """Observed vs expected phoneme at one position — evidence only, not a pass/fail."""

    position: int
    expected_phoneme: str
    observed_phoneme: str
    word: str = ""
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class PauseMarker:
    """Detected pause in speech."""

    start_sec: float
    end_sec: float
    duration_sec: float
    placement: str = ""  # e.g. clause_boundary, mid_phrase, before_content_word


@dataclass(frozen=True, slots=True)
class ProsodyFeatures:
    """Acoustic prosody evidence — language learning only, no identity/emotion claims."""

    pitch_mean_hz: float = 0.0
    pitch_std_hz: float = 0.0
    pitch_range_hz: float = 0.0
    energy_mean: float = 0.0
    energy_std: float = 0.0
    speaking_rate_wpm: float = 0.0
    articulation_rate_wpm: float = 0.0
    rhythm_regularity: float = 0.0
    phrase_final_rise: bool | None = None
    feature_version: str = "0.1.0"


@dataclass(frozen=True, slots=True)
class SpeakingAudioSession:
    """Owns the live or recorded speaking session — no educational scoring.

    Future target: LiveKit-compatible real-time sessions. Batch and streaming
    modes converge on the same downstream evidence contract.
    """

    session_id: str
    student_id: int
    language_id: int
    lesson_id: int | None
    speaking_task_id: str
    turn_number: int
    audio_source: SpeakingAudioSource
    duration_sec: float
    processing_state: SpeakingSessionProcessingState
    conversation_state: SpeakingConversationState
    media_object_id: int | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    session_version: str = SPEAKING_CORE_TYPES_VERSION

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "student_id": self.student_id,
            "language_id": self.language_id,
            "lesson_id": self.lesson_id,
            "speaking_task_id": self.speaking_task_id,
            "turn_number": self.turn_number,
            "audio_source": self.audio_source.value,
            "duration_sec": round(self.duration_sec, 3),
            "processing_state": self.processing_state.value,
            "conversation_state": self.conversation_state.value,
            "media_object_id": self.media_object_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "session_version": self.session_version,
        }


@dataclass(frozen=True, slots=True)
class SpeakingSpeechEvidence:
    """Canonical speech evidence — facts only, never pass/fail/ready/promotion.

    Downstream analysis engines consume this object. Provider SDKs must not
    leak past the Audio Frontend boundary.
    """

    session_id: str
    transcript: str
    transcript_confidence: float
    words: tuple[WordTiming, ...] = ()
    pauses: tuple[PauseMarker, ...] = ()
    speech_duration_sec: float = 0.0
    speaking_rate_wpm: float = 0.0
    articulation_rate_wpm: float = 0.0
    phoneme_alignments: tuple[PhonemeAlignment, ...] = ()
    expected_phonemes: tuple[str, ...] = ()
    observed_phonemes: tuple[str, ...] = ()
    pronunciation_confidence: float = 0.0
    embedding_ref: str = ""  # opaque storage key, not raw vector in hot path
    prosody: ProsodyFeatures = field(default_factory=ProsodyFeatures)
    hesitation_markers: tuple[str, ...] = ()
    filler_words: tuple[str, ...] = ()
    self_corrections: tuple[str, ...] = ()
    repetitions: tuple[str, ...] = ()
    abandoned_utterance: bool = False
    provider_provenance: tuple[str, ...] = ()  # e.g. transcription:openai, prosody:stub
    evidence_version: str = SPEAKING_CORE_TYPES_VERSION

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "transcript": self.transcript,
            "transcript_confidence": round(self.transcript_confidence, 4),
            "words": [
                {"word": w.word, "start_sec": w.start_sec, "end_sec": w.end_sec, "confidence": w.confidence}
                for w in self.words
            ],
            "pauses": [
                {
                    "start_sec": p.start_sec,
                    "end_sec": p.end_sec,
                    "duration_sec": p.duration_sec,
                    "placement": p.placement,
                }
                for p in self.pauses
            ],
            "speech_duration_sec": round(self.speech_duration_sec, 3),
            "speaking_rate_wpm": round(self.speaking_rate_wpm, 2),
            "articulation_rate_wpm": round(self.articulation_rate_wpm, 2),
            "phoneme_alignments": [
                {
                    "position": a.position,
                    "expected_phoneme": a.expected_phoneme,
                    "observed_phoneme": a.observed_phoneme,
                    "word": a.word,
                    "confidence": a.confidence,
                }
                for a in self.phoneme_alignments
            ],
            "pronunciation_confidence": round(self.pronunciation_confidence, 4),
            "embedding_ref": self.embedding_ref,
            "prosody": {
                "pitch_mean_hz": self.prosody.pitch_mean_hz,
                "pitch_std_hz": self.prosody.pitch_std_hz,
                "pitch_range_hz": self.prosody.pitch_range_hz,
                "energy_mean": self.prosody.energy_mean,
                "energy_std": self.prosody.energy_std,
                "speaking_rate_wpm": self.prosody.speaking_rate_wpm,
                "articulation_rate_wpm": self.prosody.articulation_rate_wpm,
                "rhythm_regularity": self.prosody.rhythm_regularity,
                "phrase_final_rise": self.prosody.phrase_final_rise,
                "feature_version": self.prosody.feature_version,
            },
            "hesitation_markers": list(self.hesitation_markers),
            "filler_words": list(self.filler_words),
            "self_corrections": list(self.self_corrections),
            "repetitions": list(self.repetitions),
            "abandoned_utterance": self.abandoned_utterance,
            "provider_provenance": list(self.provider_provenance),
            "evidence_version": self.evidence_version,
        }
