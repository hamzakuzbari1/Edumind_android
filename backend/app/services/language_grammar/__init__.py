"""Grammar spine shared infrastructure (G0).

RESPONSIBILITY: Shared enums, ownership registry, canonical grammar_id helpers,
and storage namespace constants. No progression/mastery algorithms or Claude calls.
"""

from __future__ import annotations

from app.services.language_grammar.enums import (
    GrammarCandidatePriority,
    GrammarCEFRBand,
    GrammarEvidenceSourceSkill,
    GrammarLegacyIdKind,
    GrammarLessonStepKind,
    GrammarMasteryState,
    GrammarObservationType,
    GrammarReinforcementSkill,
    GrammarReviewMode,
    GrammarReviewPriority,
    GrammarReviewReason,
)
from app.services.language_grammar.id_canon import (
    GRAMMAR_ID_PREFIX,
    assert_canonical_grammar_id,
    assert_grammar_display_code,
    is_canonical_grammar_id,
    is_grammar_display_code,
    normalize_grammar_display_code,
    normalize_grammar_id,
)
from app.services.language_grammar.ownership import (
    ALLOWED_PACKAGE_DEPENDENCIES,
    ARCHITECTURE_LAYERS,
    EVIDENCE_TO_MASTERY_BRIDGE,
    FORBIDDEN_MASTERY_WRITERS,
    GRAMMAR_JSONB_NAMESPACE,
    MASTERY_WRITE_OWNER,
    PACKAGE_LAYER,
    PACKAGE_OWNERSHIP,
    REQUIRED_G0_PACKAGES,
    SHARED_INFRASTRUCTURE,
    VOCABULARY_JSONB_NAMESPACE_RESERVED,
)
from app.services.language_grammar.types import (
    GRAMMAR_CORE_TYPES_VERSION,
    GRAMMAR_STORAGE_MASTERY_KEY,
    GRAMMAR_STORAGE_PROGRESSION_KEY,
    GRAMMAR_STORAGE_REVIEW_KEY,
    GRAMMAR_STORAGE_RUNTIME_KEY,
    GRAMMAR_STORAGE_SCHEMA_VERSION,
    GRAMMAR_STORAGE_SCHEMA_VERSION_KEY,
    GrammarStorageNamespaces,
)

PACKAGE_VERSION = "1.0.0"
# G3.5 system freeze — foundation certified before real Skills / LLM integration.
GRAMMAR_ENGINE_RELEASE = "1.0.0"
GRAMMAR_ENGINE_V1_FROZEN = True
RESPONSIBILITY = "Shared enums, ownership registry, and canonical grammar_id contracts"

__all__ = [
    "ALLOWED_PACKAGE_DEPENDENCIES",
    "ARCHITECTURE_LAYERS",
    "EVIDENCE_TO_MASTERY_BRIDGE",
    "FORBIDDEN_MASTERY_WRITERS",
    "GRAMMAR_CORE_TYPES_VERSION",
    "GRAMMAR_ENGINE_RELEASE",
    "GRAMMAR_ENGINE_V1_FROZEN",
    "GRAMMAR_ID_PREFIX",
    "GRAMMAR_JSONB_NAMESPACE",
    "GRAMMAR_STORAGE_MASTERY_KEY",
    "GRAMMAR_STORAGE_PROGRESSION_KEY",
    "GRAMMAR_STORAGE_REVIEW_KEY",
    "GRAMMAR_STORAGE_RUNTIME_KEY",
    "GRAMMAR_STORAGE_SCHEMA_VERSION",
    "GRAMMAR_STORAGE_SCHEMA_VERSION_KEY",
    "GrammarCandidatePriority",
    "GrammarCEFRBand",
    "GrammarEvidenceSourceSkill",
    "GrammarLegacyIdKind",
    "GrammarLessonStepKind",
    "GrammarMasteryState",
    "GrammarObservationType",
    "GrammarReinforcementSkill",
    "GrammarReviewMode",
    "GrammarReviewPriority",
    "GrammarReviewReason",
    "GrammarStorageNamespaces",
    "MASTERY_WRITE_OWNER",
    "PACKAGE_LAYER",
    "PACKAGE_OWNERSHIP",
    "PACKAGE_VERSION",
    "REQUIRED_G0_PACKAGES",
    "RESPONSIBILITY",
    "SHARED_INFRASTRUCTURE",
    "VOCABULARY_JSONB_NAMESPACE_RESERVED",
    "assert_canonical_grammar_id",
    "assert_grammar_display_code",
    "is_canonical_grammar_id",
    "is_grammar_display_code",
    "normalize_grammar_display_code",
    "normalize_grammar_id",
]
