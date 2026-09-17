"""Speaking provider capability contracts (S0) — no implementations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TranscriptionCapabilities:
    """What the active SpeechTranscriptionProvider supports."""

    supports_word_timestamps: bool = False
    supports_confidence_scores: bool = False
    supports_streaming: bool = False
    supported_languages: tuple[str, ...] = ("en",)
    provider_name: str = ""


@dataclass(frozen=True, slots=True)
class EmbeddingCapabilities:
    """Speech embedding provider capabilities."""

    embedding_dim: int = 0
    supports_streaming: bool = False
    storage_external: bool = True  # vectors stored by ref, not inline
    provider_name: str = ""


@dataclass(frozen=True, slots=True)
class PhonemeAlignmentCapabilities:
    """Phoneme alignment provider capabilities."""

    supports_forced_alignment: bool = False
    supports_phoneme_confidence: bool = False
    min_audio_duration_sec: float = 0.0
    provider_name: str = ""


@dataclass(frozen=True, slots=True)
class AcousticFeatureCapabilities:
    """OpenSMILE/Praat-compatible acoustic feature extraction capabilities."""

    supports_pitch: bool = False
    supports_energy: bool = False
    supports_rhythm: bool = False
    supports_stress: bool = False
    provider_name: str = ""


@dataclass(frozen=True, slots=True)
class SpeechOutputCapabilities:
    """TTS / speech synthesis provider capabilities.

    Do not claim unsupported emotional or prosodic controls.
    """

    supports_voice_selection: bool = True
    supports_speaking_rate: bool = False
    supports_multi_segment: bool = False
    supports_delivery_metadata: bool = False
    supported_languages: tuple[str, ...] = ("en",)
    provider_name: str = "supertonic"


@dataclass(frozen=True, slots=True)
class EducationalAnalyzerCapabilities:
    """LLM educational analyzer capabilities."""

    supports_structured_json: bool = True
    supports_coach_guidance: bool = False
    max_output_tokens: int = 0
    provider_name: str = ""


@dataclass(frozen=True, slots=True)
class LiveConversationCapabilities:
    """Hume EVI / live speech-to-speech provider capabilities."""

    supports_barge_in: bool = True
    supports_expression_measures: bool = True
    supports_custom_llm: bool = True
    supports_streaming_audio: bool = True
    provider_name: str = ""
