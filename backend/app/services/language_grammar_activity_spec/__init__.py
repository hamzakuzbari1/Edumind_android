"""Grammar Activity Specification Framework (G3.35).

RESPONSIBILITY: Canonical ActivitySpecification contract between Activity Providers
and future Skill Executors / Renderers. No UI, no Runtime state, no Claude, no execution.
"""

from __future__ import annotations

from app.services.language_grammar_activity_spec.builders import build_minimal_specification, loc
from app.services.language_grammar_activity_spec.enums import (
    ACTIVITY_SCHEMA_VERSION,
    ACTIVITY_SPEC_PACKAGE_VERSION,
    GRAMMAR_SCHEMA_VERSION,
    ActivityDifficulty,
    ActivityType,
    EvaluationMode,
    EvidenceKind,
    ExpectedOutputType,
)
from app.services.language_grammar_activity_spec.flags import (
    activity_spec_validation_strict,
    grammar_engine_enabled,
)
from app.services.language_grammar_activity_spec.registry import (
    ActivitySpecRegistry,
    get_default_spec_registry,
    reset_default_spec_registry_for_tests,
)
from app.services.language_grammar_activity_spec.serialization import (
    fingerprint_specification,
    specification_from_dict,
    specification_to_dict,
    with_fingerprint,
)
from app.services.language_grammar_activity_spec.types import (
    ActivityAssetRef,
    ActivityReference,
    ActivitySpecification,
    ActivityVersionSet,
    CompletionRule,
    EvidenceDeclaration,
    ExpectedOutputSpec,
    LocalizedText,
    ProviderMetadata,
)
from app.services.language_grammar_activity_spec.validation import (
    ActivitySpecError,
    validate_activity_specification,
)

PACKAGE_VERSION = ACTIVITY_SPEC_PACKAGE_VERSION
RESPONSIBILITY = (
    "Canonical ActivitySpecification models, validation, serialization, and registry"
)

__all__ = [
    "ACTIVITY_SCHEMA_VERSION",
    "ACTIVITY_SPEC_PACKAGE_VERSION",
    "GRAMMAR_SCHEMA_VERSION",
    "ActivityAssetRef",
    "ActivityDifficulty",
    "ActivityReference",
    "ActivitySpecError",
    "ActivitySpecRegistry",
    "ActivitySpecification",
    "ActivityType",
    "ActivityVersionSet",
    "CompletionRule",
    "EvaluationMode",
    "EvidenceDeclaration",
    "EvidenceKind",
    "ExpectedOutputSpec",
    "ExpectedOutputType",
    "LocalizedText",
    "PACKAGE_VERSION",
    "ProviderMetadata",
    "RESPONSIBILITY",
    "activity_spec_validation_strict",
    "build_minimal_specification",
    "fingerprint_specification",
    "get_default_spec_registry",
    "grammar_engine_enabled",
    "loc",
    "reset_default_spec_registry_for_tests",
    "specification_from_dict",
    "specification_to_dict",
    "validate_activity_specification",
    "with_fingerprint",
]
