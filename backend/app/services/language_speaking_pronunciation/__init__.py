"""Speaking pronunciation facts layer (S5).

RESPONSIBILITY: Phoneme/word/phrase pronunciation facts — evidence only.
"""

from app.services.language_speaking_pronunciation.assembler import assemble_pronunciation_evidence
from app.services.language_speaking_pronunciation.types import (
    LANGUAGE_SPEAKING_PRONUNCIATION_SCHEMA_VERSION,
    LANGUAGE_SPEAKING_PRONUNCIATION_VERSION,
    PhonemeAlignmentOperation,
    PhonemeObservation,
    PronunciationAnalysisFacts,
    PronunciationIssueObservation,
    PronunciationProvenance,
    PronunciationReferenceSource,
    SpeakingPronunciationEvidenceResult,
    WordPronunciationObservation,
)

__all__ = [
    "LANGUAGE_SPEAKING_PRONUNCIATION_SCHEMA_VERSION",
    "LANGUAGE_SPEAKING_PRONUNCIATION_VERSION",
    "PhonemeAlignmentOperation",
    "PhonemeObservation",
    "PronunciationAnalysisFacts",
    "PronunciationIssueObservation",
    "PronunciationProvenance",
    "PronunciationReferenceSource",
    "SpeakingPronunciationEvidenceResult",
    "WordPronunciationObservation",
    "assemble_pronunciation_evidence",
]
