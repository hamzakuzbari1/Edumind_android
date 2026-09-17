"""Retry policy helpers for LLM Activity Authoring (V1.4)."""

from __future__ import annotations

from app.services.language_grammar_activity_authoring.llm.errors import (
    LLMAuthoringError,
    LLMInvalidJSONError,
    LLMSchemaError,
    LLMTimeoutError,
    LLMTransientError,
)
from app.services.language_grammar_activity_authoring.llm.types import RetryPolicy

# Re-export for callers that import RetryPolicy from retry.
__all__ = ["RetryPolicy", "should_retry", "classify_exception"]


def classify_exception(exc: BaseException) -> str:
    if isinstance(exc, LLMTimeoutError):
        return "timeout"
    if isinstance(exc, LLMInvalidJSONError):
        return "invalid_json"
    if isinstance(exc, LLMSchemaError):
        return "schema_validation_failure"
    if isinstance(exc, LLMTransientError):
        return "transient_failure"
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, LLMAuthoringError):
        return "provider_error"
    return "transient_failure"


def should_retry(exc: BaseException, policy: RetryPolicy) -> bool:
    reason = classify_exception(exc)
    if reason == "timeout":
        return policy.retry_on_timeout
    if reason == "invalid_json":
        return policy.retry_on_invalid_json
    if reason == "schema_validation_failure":
        return policy.retry_on_schema_failure
    if reason == "transient_failure":
        return policy.retry_on_transient
    return False
