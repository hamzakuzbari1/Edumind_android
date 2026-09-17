"""Speaking provider ABCs (S0).

RESPONSIBILITY: Provider interface contracts and capability dataclasses.
No WhisperX, WavLM, SpeechBrain, OpenSMILE, Praat, LiveKit, or ElevenLabs
implementations in S0.
"""

from app.services.language_speaking_providers.types import (
    AcousticFeatureCapabilities,
    AcousticFeatureProvider,
    EducationalAnalyzerCapabilities,
    EmbeddingCapabilities,
    PhonemeAlignmentCapabilities,
    PhonemeAlignmentProvider,
    SpeakingEducationalAnalyzerProvider,
    SpeakingSpeechOutputProvider,
    SpeechEmbeddingProvider,
    SpeechOutputCapabilities,
    SpeechTranscriptionProvider,
    TranscriptionCapabilities,
)

__all__ = [
    "AcousticFeatureCapabilities",
    "AcousticFeatureProvider",
    "EducationalAnalyzerCapabilities",
    "EmbeddingCapabilities",
    "PhonemeAlignmentCapabilities",
    "PhonemeAlignmentProvider",
    "SpeakingEducationalAnalyzerProvider",
    "SpeakingSpeechOutputProvider",
    "SpeechEmbeddingProvider",
    "SpeechOutputCapabilities",
    "SpeechTranscriptionProvider",
    "TranscriptionCapabilities",
]
