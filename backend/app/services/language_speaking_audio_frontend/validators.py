"""Validation helpers for audio frontend contracts (S3).

Pure validation — no provider SDKs, no educational scoring.
"""

from __future__ import annotations

from app.services.language_speaking_audio_frontend.enums import AudioEvidenceQualityFlag
from app.services.language_speaking_audio_frontend.evidence import (
    PhonemeAlignmentEntry,
    PhonemeAlignmentEvidence,
    ProsodyFeatureEvidence,
    SpeechEmbeddingEvidence,
    TranscriptEvidence,
    TranscriptSegment,
)
from app.services.language_speaking.types import WordTiming

# Educational judgement fields that MUST NOT appear in evidence contracts.
FORBIDDEN_EDUCATIONAL_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "pass",
        "fail",
        "passed",
        "failed",
        "mastery",
        "readiness",
        "promotion",
        "promotion_status",
        "lesson_completed",
        "lesson_completion",
        "cefr",
        "official_speaking_cefr",
        "next_lesson",
        "score",
        "grade",
    }
)


def validate_word_timestamps_ordered(words: tuple[WordTiming, ...]) -> list[str]:
    """Return validation errors if word timestamps are not monotonically ordered."""
    errors: list[str] = []
    for i, w in enumerate(words):
        if w.end_sec < w.start_sec:
            errors.append(f"word[{i}] end_sec < start_sec: {w.word}")
        if i > 0 and w.start_sec < words[i - 1].start_sec:
            errors.append(f"word[{i}] start_sec before word[{i - 1}].start_sec")
    return errors


def validate_segment_timestamps_ordered(segments: tuple[TranscriptSegment, ...]) -> list[str]:
    """Return validation errors if segment timestamps are not monotonically ordered."""
    errors: list[str] = []
    for i, s in enumerate(segments):
        if s.end_sec < s.start_sec:
            errors.append(f"segment[{i}] end_sec < start_sec")
        if i > 0 and s.start_sec < segments[i - 1].start_sec:
            errors.append(f"segment[{i}] start_sec before segment[{i - 1}].start_sec")
    return errors


def validate_phoneme_alignment_timestamps(
    alignments: tuple[PhonemeAlignmentEntry, ...],
) -> list[str]:
    """Return validation errors for phoneme alignment timestamp ordering."""
    errors: list[str] = []
    for i, a in enumerate(alignments):
        if a.end_sec < a.start_sec:
            errors.append(f"alignment[{i}] end_sec < start_sec at position {a.position}")
        if i > 0 and a.start_sec < alignments[i - 1].start_sec:
            errors.append(f"alignment[{i}] start_sec before alignment[{i - 1}].start_sec")
    return errors


def validate_embedding_metadata(evidence: SpeechEmbeddingEvidence) -> list[str]:
    """Return validation errors for embedding evidence metadata."""
    errors: list[str] = []
    if not evidence.embedding_reference:
        errors.append("embedding_reference is required")
    if not evidence.model_identifier:
        errors.append("model_identifier is required")
    if evidence.embedding_dimension <= 0:
        errors.append(f"embedding_dimension must be positive, got {evidence.embedding_dimension}")
    return errors


def validate_transcript_evidence(evidence: TranscriptEvidence) -> list[str]:
    """Return validation errors for transcript evidence."""
    errors: list[str] = []
    if not evidence.text and not evidence.segments:
        errors.append("transcript must have text or segments")
    errors.extend(validate_word_timestamps_ordered(evidence.words))
    errors.extend(validate_segment_timestamps_ordered(evidence.segments))
    return errors


def validate_phoneme_alignment_evidence(evidence: PhonemeAlignmentEvidence) -> list[str]:
    """Return validation errors for phoneme alignment evidence."""
    errors: list[str] = []
    if not evidence.alignments:
        errors.append("phoneme alignment evidence must have at least one alignment entry")
    errors.extend(validate_phoneme_alignment_timestamps(evidence.alignments))
    return errors


def validate_prosody_evidence(evidence: ProsodyFeatureEvidence) -> list[str]:
    """Return validation errors for prosody evidence (minimal structural checks)."""
    errors: list[str] = []
    if evidence.speaking_rate.words_per_minute < 0:
        errors.append("speaking_rate.words_per_minute must be non-negative")
    if evidence.pause.pause_count < 0:
        errors.append("pause.pause_count must be non-negative")
    return errors


def validate_no_educational_fields_in_dict(data: dict[str, object], *, path: str = "") -> list[str]:
    """Recursively scan a persistence dict for forbidden educational field names."""
    errors: list[str] = []
    for key, value in data.items():
        full_path = f"{path}.{key}" if path else key
        if key.lower() in FORBIDDEN_EDUCATIONAL_FIELD_NAMES:
            errors.append(f"forbidden educational field: {full_path}")
        if isinstance(value, dict):
            errors.extend(validate_no_educational_fields_in_dict(value, path=full_path))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    errors.extend(
                        validate_no_educational_fields_in_dict(item, path=f"{full_path}[{i}]")
                    )
    return errors


def quality_flags_from_partial_availability(
    availability: dict[str, bool],
) -> tuple[AudioEvidenceQualityFlag, ...]:
    """Derive explicit quality flags when evidence families are unavailable."""
    flags: list[AudioEvidenceQualityFlag] = []
    if not availability.get("transcript", True):
        flags.append(AudioEvidenceQualityFlag.partial_processing)
    if not availability.get("phoneme_alignment", True):
        flags.append(AudioEvidenceQualityFlag.alignment_unavailable)
    if not availability.get("prosody", True):
        flags.append(AudioEvidenceQualityFlag.prosody_unavailable)
    if not availability.get("speech_embedding", True):
        flags.append(AudioEvidenceQualityFlag.partial_processing)
    return tuple(flags)
