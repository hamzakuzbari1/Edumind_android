"""Speaking educational_analyzer (S7) — LLM educational facts JSON only.

RESPONSIBILITY: Claude/mock educational analysis JSON — never pass/fail/promotion.
"""

from app.services.language_speaking_educational_analyzer.analyzer import analyze_speaking_turn_educationally
from app.services.language_speaking_educational_analyzer.types import (
    ANALYZER_FACTS_VERSION,
    SpeakingAnalysisContext,
    SpeakingEducationalFacts,
    unavailable_speaking_facts,
)

__all__ = [
    "ANALYZER_FACTS_VERSION",
    "SpeakingAnalysisContext",
    "SpeakingEducationalFacts",
    "analyze_speaking_turn_educationally",
    "unavailable_speaking_facts",
]
