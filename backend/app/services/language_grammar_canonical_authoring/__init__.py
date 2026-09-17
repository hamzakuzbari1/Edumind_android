"""Offline canonical grammar lesson authoring workflow."""

from app.services.language_grammar_canonical_authoring.adapters import (
    ExistingLLMCanonicalAuthoringAdapter,
    ExistingLLMSectionedCanonicalAuthoringAdapter,
    FixtureCanonicalAuthoringAdapter,
    FixtureSectionedCanonicalAuthoringAdapter,
)
from app.services.language_grammar_canonical_authoring.errors import (
    GrammarCanonicalAuthoringWorkflowError,
)
from app.services.language_grammar_canonical_authoring.types import (
    CanonicalAuthoringAdapter,
    CanonicalAuthoringAdapterRequest,
    CanonicalAuthoringAdapterResult,
    CanonicalLessonIdentityInput,
    RevisionValidationResult,
    SectionedAuthoringUnitResult,
    SectionedCanonicalAuthoringAdapter,
    UnitValidationResult,
    WorkflowCommandResult,
)
from app.services.language_grammar_canonical_authoring.sectioned_workflow import (
    assemble_sectioned_revision,
    generate_sectioned_draft_revision,
    inspect_unit_attempt,
    list_revision_unit_attempts,
    retry_unit_attempt,
    supersede_unit_attempt,
)
from app.services.language_grammar_canonical_authoring.workflow import (
    archive_canonical_revision,
    ensure_identity,
    generate_draft_revision,
    inspect_revision,
    list_canonical_revisions,
    normalize_identity_input,
    publish_revision,
    retry_failed_revision,
    validate_revision,
)

PACKAGE = "language_grammar_canonical_authoring"
RESPONSIBILITY = (
    "Offline operator-controlled canonical grammar lesson identity, revision, "
    "validation, inspection, publishing, archiving, and retry workflow."
)

__all__ = [
    "PACKAGE",
    "RESPONSIBILITY",
    "CanonicalAuthoringAdapter",
    "CanonicalAuthoringAdapterRequest",
    "CanonicalAuthoringAdapterResult",
    "CanonicalLessonIdentityInput",
    "ExistingLLMCanonicalAuthoringAdapter",
    "ExistingLLMSectionedCanonicalAuthoringAdapter",
    "FixtureCanonicalAuthoringAdapter",
    "FixtureSectionedCanonicalAuthoringAdapter",
    "GrammarCanonicalAuthoringWorkflowError",
    "RevisionValidationResult",
    "SectionedAuthoringUnitResult",
    "SectionedCanonicalAuthoringAdapter",
    "UnitValidationResult",
    "WorkflowCommandResult",
    "assemble_sectioned_revision",
    "archive_canonical_revision",
    "ensure_identity",
    "generate_draft_revision",
    "generate_sectioned_draft_revision",
    "inspect_revision",
    "inspect_unit_attempt",
    "list_canonical_revisions",
    "list_revision_unit_attempts",
    "normalize_identity_input",
    "publish_revision",
    "retry_failed_revision",
    "retry_unit_attempt",
    "supersede_unit_attempt",
    "validate_revision",
]
