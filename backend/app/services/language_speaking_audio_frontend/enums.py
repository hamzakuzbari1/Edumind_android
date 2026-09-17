"""Audio frontend enums (S3) — provider-neutral vocabulary.

All values here are infrastructure/evidence vocabulary. None of them encode
educational judgement (pass/fail, mastery, readiness, promotion).
"""

from __future__ import annotations

from enum import StrEnum


class AudioArtifactKind(StrEnum):
    """Distinguishes the raw upload from its normalized derivative."""

    raw = "raw"
    normalized = "normalized"


class SpeakingEvidenceFamily(StrEnum):
    """The four provider-neutral audio evidence families."""

    transcript = "transcript"
    speech_embedding = "speech_embedding"
    phoneme_alignment = "phoneme_alignment"
    prosody = "prosody"


class ProviderCapabilityFlag(StrEnum):
    """Capabilities a provider may declare. No provider is assumed to support all.

    Future provider composition example:
      WhisperX      -> transcription + word/segment timestamps + phoneme_alignment
      WavLM/HuBERT  -> speech_embeddings
      SpeechBrain   -> pronunciation_features + phoneme_alignment
      OpenSMILE/Praat -> pitch/energy/pauses/rhythm/stress/intonation
      LiveKit       -> streaming transport
    """

    transcription = "transcription"
    word_timestamps = "word_timestamps"
    segment_timestamps = "segment_timestamps"
    speech_embeddings = "speech_embeddings"
    phoneme_alignment = "phoneme_alignment"
    pronunciation_features = "pronunciation_features"
    pitch = "pitch"
    energy = "energy"
    pauses = "pauses"
    speaking_rate = "speaking_rate"
    rhythm = "rhythm"
    stress = "stress"
    intonation = "intonation"
    streaming = "streaming"


class AudioEvidenceQualityFlag(StrEnum):
    """Provider-neutral evidence reliability context.

    Quality metadata describes how trustworthy the evidence is. It MUST NOT
    directly decide student mastery — downstream educational engines weigh it.
    """

    low_audio_quality = "low_audio_quality"
    clipping_detected = "clipping_detected"
    excessive_background_noise = "excessive_background_noise"
    audio_too_short = "audio_too_short"
    audio_too_long = "audio_too_long"
    timestamp_unavailable = "timestamp_unavailable"
    alignment_unavailable = "alignment_unavailable"
    prosody_unavailable = "prosody_unavailable"
    unsupported_codec = "unsupported_codec"
    partial_processing = "partial_processing"
