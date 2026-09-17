"""Speaking provider interfaces (S0 stubs)."""

from app.services.language_speaking_providers.capabilities import (
    AcousticFeatureCapabilities,
    EducationalAnalyzerCapabilities,
    EmbeddingCapabilities,
    PhonemeAlignmentCapabilities,
    SpeechOutputCapabilities,
    TranscriptionCapabilities,
)
from app.services.language_speaking_providers.providers import (
    AcousticFeatureProvider,
    PhonemeAlignmentProvider,
    SpeakingEducationalAnalyzerProvider,
    SpeakingSpeechOutputProvider,
    SpeechEmbeddingProvider,
    SpeechTranscriptionProvider,
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
