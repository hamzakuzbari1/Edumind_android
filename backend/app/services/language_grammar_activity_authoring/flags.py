"""Feature flags for Grammar Activity Authoring (V1.3)."""

from __future__ import annotations

from app.core.config import get_settings


def grammar_engine_enabled() -> bool:
    return bool(get_settings().LANG_GRAMMAR_ENGINE_ENABLED)


def activity_authoring_enabled() -> bool:
    settings = get_settings()
    return bool(settings.LANG_GRAMMAR_ENGINE_ENABLED) and bool(
        getattr(settings, "LANG_GRAMMAR_ACTIVITY_AUTHORING_ENABLED", True)
    )


def activity_authoring_strict() -> bool:
    return bool(getattr(get_settings(), "LANG_GRAMMAR_ACTIVITY_AUTHORING_STRICT", True))
