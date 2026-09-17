"""Offline canonical grammar lesson authoring workflow contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from app.services.language_grammar_activity_authoring.llm.lesson_schema import (
    CANONICAL_LESSON_SCHEMA_VERSION,
    METHODOLOGY_VERSION,
)
from app.services.language_grammar_catalog.types import GRAMMAR_CATALOG_VERSION

DEFAULT_SCHEMA_VERSION = CANONICAL_LESSON_SCHEMA_VERSION
DEFAULT_METHODOLOGY_VERSION = METHODOLOGY_VERSION
DEFAULT_PROMPT_VERSION = "offline_adapter"
DEFAULT_CATALOG_VERSION = GRAMMAR_CATALOG_VERSION
SUPPORTED_AUTHORING_LOCALES = frozenset({"en", "en-US", "ar", "ar-SY"})
SECTIONED_UNIT_KEYS = ("blueprint", "concept", "examples", "rules", "practice", "production")
LEARNER_UNIT_KEYS = ("concept", "examples", "rules", "practice", "production")
UNIT_ATTEMPT_STATUSES = ("pending", "generating", "validating", "accepted", "failed", "superseded")


@dataclass(frozen=True, slots=True)
class CanonicalLessonIdentityInput:
    grammar_id: str
    cefr_level: str
    locale: str = "ar-SY"
    methodology_version: str = DEFAULT_METHODOLOGY_VERSION


@dataclass(frozen=True, slots=True)
class CanonicalAuthoringAdapterRequest:
    grammar_id: str
    display_name: str
    cefr_level: str
    locale: str
    methodology_version: str
    schema_version: str = DEFAULT_SCHEMA_VERSION
    prompt_version: str = DEFAULT_PROMPT_VERSION
    catalog_version: str = DEFAULT_CATALOG_VERSION
    grammar_profile: dict[str, Any] = field(default_factory=dict)
    learner_signals: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CanonicalAuthoringAdapterResult:
    success: bool
    student_content_json: dict[str, Any] | None = None
    server_teaching_metadata_json: dict[str, Any] | None = None
    raw_response_text: str | None = None
    provider_id: str = "fixture"
    authoring_model: str = "fixture"
    schema_version: str = DEFAULT_SCHEMA_VERSION
    prompt_version: str = DEFAULT_PROMPT_VERSION
    catalog_version: str = DEFAULT_CATALOG_VERSION
    stop_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    raw_artifact_ref: str | None = None
    diagnostics_json: dict[str, Any] = field(default_factory=dict)
    generated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SectionedAuthoringUnitResult:
    success: bool
    structured_payload: dict[str, Any] | None = None
    private_metadata_json: dict[str, Any] | None = None
    raw_response_text: str | None = None
    provider_id: str = "fixture"
    authoring_model: str = "fixture"
    prompt_version: str = DEFAULT_PROMPT_VERSION
    stop_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    truncated: bool | None = None
    json_parse_passed: bool | None = None
    raw_artifact_ref: str | None = None
    diagnostics_json: dict[str, Any] = field(default_factory=dict)
    generated_at: datetime | None = None


@runtime_checkable
class CanonicalAuthoringAdapter(Protocol):
    """Offline workflow boundary around any grammar lesson authoring provider."""

    def generate(self, request: CanonicalAuthoringAdapterRequest) -> CanonicalAuthoringAdapterResult:
        """Return raw or structured authoring output. Implementations own provider details."""
        ...


@runtime_checkable
class SectionedCanonicalAuthoringAdapter(Protocol):
    """Provider boundary for blueprint + five independent unit authoring."""

    def generate_blueprint(self, request: CanonicalAuthoringAdapterRequest) -> SectionedAuthoringUnitResult:
        """Generate the server-private blueprint unit."""
        ...

    def generate_unit(
        self,
        unit_key: str,
        blueprint: dict[str, Any],
        accepted_prior_units: dict[str, dict[str, Any]],
        request: CanonicalAuthoringAdapterRequest,
    ) -> SectionedAuthoringUnitResult:
        """Generate one learner-facing unit without knowing provider internals."""
        ...


@dataclass(frozen=True, slots=True)
class WorkflowCommandResult:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error_code: str = ""
    message: str = ""


@dataclass(frozen=True, slots=True)
class RevisionValidationResult:
    valid: bool
    diagnostics_json: dict[str, Any] = field(default_factory=dict)
    normalized_student_content: dict[str, Any] | None = None
    normalized_server_teaching_metadata: dict[str, Any] | None = None
    content_hash: str | None = None


@dataclass(frozen=True, slots=True)
class UnitValidationResult:
    valid: bool
    diagnostics_json: dict[str, Any] = field(default_factory=dict)
    normalized_public_payload: dict[str, Any] | None = None
    normalized_private_metadata: dict[str, Any] | None = None
    normalized_blueprint: dict[str, Any] | None = None
    content_hash: str | None = None
