"""Feature flags for Activity Specification Framework (G3.35)."""

from __future__ import annotations

from app.core.config import get_settings


def grammar_engine_enabled() -> bool:
    return bool(get_settings().LANG_GRAMMAR_ENGINE_ENABLED)


def activity_spec_validation_strict() -> bool:
    """When true (default), validate_activity_specification is mandatory before accept."""
    return bool(getattr(get_settings(), "LANG_GRAMMAR_ACTIVITY_SPEC_STRICT", True))
