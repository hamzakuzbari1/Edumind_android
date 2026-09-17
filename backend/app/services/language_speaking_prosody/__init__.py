"""Speaking prosody facts layer (S6).

RESPONSIBILITY: Pitch, stress, rhythm, intonation, pause, delivery facts — evidence only.
"""

from app.services.language_speaking_prosody.assembler import assemble_prosody_evidence
from app.services.language_speaking_prosody.types import (
    LANGUAGE_SPEAKING_PROSODY_SCHEMA_VERSION,
    LANGUAGE_SPEAKING_PROSODY_VERSION,
    ExpressionObservation,
    ProsodyAnalysisFacts,
    ProsodyEvidenceSource,
    ProsodyIssueObservation,
    ProsodyProvenance,
    ProsodySignalObservation,
    SpeakingProsodyEvidenceResult,
    TurnSegmentObservation,
)

__all__ = [
    "LANGUAGE_SPEAKING_PROSODY_SCHEMA_VERSION",
    "LANGUAGE_SPEAKING_PROSODY_VERSION",
    "ExpressionObservation",
    "ProsodyAnalysisFacts",
    "ProsodyEvidenceSource",
    "ProsodyIssueObservation",
    "ProsodyProvenance",
    "ProsodySignalObservation",
    "SpeakingProsodyEvidenceResult",
    "TurnSegmentObservation",
    "assemble_prosody_evidence",
]
