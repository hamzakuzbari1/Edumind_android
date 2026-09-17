"""LLM Activity Authoring errors (V1.4)."""

from __future__ import annotations

from app.services.language_grammar_activity_authoring.errors import ActivityAuthoringError


class LLMAuthoringError(ActivityAuthoringError):
    """Base LLM authoring error."""


class LLMTransientError(LLMAuthoringError):
    """Transient provider / network failure."""


class LLMTimeoutError(LLMAuthoringError):
    """Provider timed out."""


class LLMInvalidJSONError(LLMAuthoringError):
    """Provider returned non-JSON or unparseable JSON."""


class LLMSchemaError(LLMAuthoringError):
    """Parsed JSON failed ActivitySpecification / request validation."""


class LLMProviderError(LLMAuthoringError):
    """Provider missing, disabled, or not implemented."""
