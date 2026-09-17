"""Feature flags for Grammar Learning Pipeline (Integration Phase 1)."""

from __future__ import annotations

from app.core.config import get_settings


def grammar_engine_enabled() -> bool:
    return bool(get_settings().LANG_GRAMMAR_ENGINE_ENABLED)


def grammar_pipeline_enabled() -> bool:
    settings = get_settings()
    return bool(grammar_engine_enabled()) and bool(
        getattr(settings, "LANG_GRAMMAR_PIPELINE_ENABLED", False)
    )


def grammar_pipeline_strict() -> bool:
    return bool(getattr(get_settings(), "LANG_GRAMMAR_PIPELINE_STRICT", True))
