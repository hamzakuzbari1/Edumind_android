"""Feature flags for LLM Activity Authoring (V1.4)."""

from __future__ import annotations

from app.core.config import get_settings
from app.services.language_grammar_activity_authoring.flags import activity_authoring_enabled
from app.services.language_grammar_activity_authoring.llm.types import RetryPolicy


def llm_authoring_enabled() -> bool:
    settings = get_settings()
    return bool(activity_authoring_enabled()) and bool(
        getattr(settings, "LANG_GRAMMAR_LLM_AUTHORING_ENABLED", False)
    )


def llm_authoring_fallback_enabled() -> bool:
    return bool(getattr(get_settings(), "LANG_GRAMMAR_LLM_AUTHORING_FALLBACK", True))


def configured_llm_authoring_provider_id() -> str:
    raw = str(getattr(get_settings(), "LANG_GRAMMAR_LLM_AUTHORING_PROVIDER", "claude") or "claude")
    return raw.strip().lower() or "claude"


def llm_authoring_timeout_seconds() -> float:
    return float(getattr(get_settings(), "LANG_GRAMMAR_LLM_AUTHORING_TIMEOUT_SECONDS", 60.0) or 60.0)


def llm_authoring_retry_policy() -> RetryPolicy:
    settings = get_settings()
    max_attempts = int(getattr(settings, "LANG_GRAMMAR_LLM_AUTHORING_MAX_RETRIES", 3) or 3)
    return RetryPolicy(max_attempts=max(1, max_attempts))
