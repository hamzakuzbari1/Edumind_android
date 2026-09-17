"""Feature flags for Grammar Skill Execution Framework (G3.4 + V1.5)."""

from __future__ import annotations

from app.core.config import get_settings
from app.services.language_grammar_skill_executor.types import ExecutionFeatureFlags


def grammar_engine_enabled() -> bool:
    return bool(get_settings().LANG_GRAMMAR_ENGINE_ENABLED)


def skill_executor_enabled() -> bool:
    """Framework gate — requires grammar engine + skill executor flag."""
    settings = get_settings()
    return bool(settings.LANG_GRAMMAR_ENGINE_ENABLED) and bool(
        getattr(settings, "LANG_GRAMMAR_SKILL_EXECUTOR_ENABLED", False)
    )


def skill_executor_strict() -> bool:
    """When true (default), reject broken specs / unknown types before execute."""
    return bool(getattr(get_settings(), "LANG_GRAMMAR_SKILL_EXECUTOR_STRICT", True))


def skill_execution_engine_enabled() -> bool:
    """V1.5 Execution Service gate — requires skill executor + engine flag."""
    settings = get_settings()
    engine_flag = bool(getattr(settings, "LANG_GRAMMAR_SKILL_EXECUTION_ENGINE_ENABLED", True))
    return skill_executor_enabled() and engine_flag


def snapshot_feature_flags() -> ExecutionFeatureFlags:
    return ExecutionFeatureFlags(
        grammar_engine_enabled=grammar_engine_enabled(),
        skill_executor_enabled=skill_executor_enabled(),
        skill_executor_strict=skill_executor_strict(),
    )
