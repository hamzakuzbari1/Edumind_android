"""Grammar Evidence (G2.2) — normalize/validate skill-emitted observations.

RESPONSIBILITY: Typed evidence contracts + catalog validation.
Mastery is the sole scorer/consumer of validated evidence.
"""

from __future__ import annotations

from app.services.language_grammar_evidence.types import (
    GrammarEvidenceBatch,
    GrammarEvidenceConsumerPort,
    GrammarEvidenceObservation,
)
from app.services.language_grammar_evidence.validation import (
    EvidenceValidationResult,
    GrammarEvidenceError,
    validate_batch,
    validate_observation,
)

PACKAGE_VERSION = "1.0.0"
RESPONSIBILITY = (
    "Normalize skill-emitted Grammar Evidence; sole translator into mastery update requests"
)

__all__ = [
    "EvidenceValidationResult",
    "GrammarEvidenceBatch",
    "GrammarEvidenceConsumerPort",
    "GrammarEvidenceError",
    "GrammarEvidenceObservation",
    "PACKAGE_VERSION",
    "RESPONSIBILITY",
    "validate_batch",
    "validate_observation",
]
