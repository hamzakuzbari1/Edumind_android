"""Speaking diagnostic (S9).

RESPONSIBILITY: Deterministic next-skill selection from graph + mastery gaps.
"""

from app.services.language_speaking_diagnostic.selector import select_speaking_target
from app.services.language_speaking_diagnostic.types import (
    LANGUAGE_SPEAKING_DIAGNOSTIC_VERSION,
    DiagnosticRecommendation,
    TargetSelectionReason,
)

__all__ = [
    "DiagnosticRecommendation",
    "LANGUAGE_SPEAKING_DIAGNOSTIC_VERSION",
    "TargetSelectionReason",
    "select_speaking_target",
]
