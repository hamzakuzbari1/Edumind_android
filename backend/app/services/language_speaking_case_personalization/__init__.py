"""Educational Case Personalization Engine — HOW students experience a case.

RESPONSIBILITY: Adapt Educational Case experience fields only (world, setting,
characters, examples, culture, memory, interests). Curriculum Engine still owns
WHAT (CEFR, vocabulary, grammar, objectives, difficulty, case_category,
case_archetype); this package never changes curriculum-locked fields.
"""

from app.services.language_speaking_case_personalization.engine import (
    apply_case_personalization,
    build_personalization_directive,
    signals_are_substantive,
)
from app.services.language_speaking_case_personalization.memory import (
    SPEAKING_CASE_MEMORY_KEY,
    case_memory_from_payload,
    merge_case_memory_into_payload,
    record_completed_case,
)
from app.services.language_speaking_case_personalization.signals import (
    build_signals_from_parts,
    collect_case_personalization_signals,
)
from app.services.language_speaking_case_personalization.types import (
    CURRICULUM_LOCKED_KEYS,
    PERSONALIZATION_ENGINE_VERSION,
    CaseMemoryLedger,
    PersonalizationDirective,
    StudentCaseSignals,
)
from app.services.language_speaking_case_personalization.validation import (
    PersonalizationGuardError,
    assert_curriculum_unchanged,
    snapshot_curriculum_fields,
)

__all__ = [
    "CURRICULUM_LOCKED_KEYS",
    "PERSONALIZATION_ENGINE_VERSION",
    "SPEAKING_CASE_MEMORY_KEY",
    "CaseMemoryLedger",
    "PersonalizationDirective",
    "PersonalizationGuardError",
    "StudentCaseSignals",
    "apply_case_personalization",
    "assert_curriculum_unchanged",
    "build_personalization_directive",
    "build_signals_from_parts",
    "case_memory_from_payload",
    "collect_case_personalization_signals",
    "merge_case_memory_into_payload",
    "record_completed_case",
    "signals_are_substantive",
    "snapshot_curriculum_fields",
]
