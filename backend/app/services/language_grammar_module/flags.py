"""Feature flags for Student Grammar Module (Product Milestone A)."""

from __future__ import annotations

from app.core.config import get_settings


def grammar_engine_enabled() -> bool:
    return bool(get_settings().LANG_GRAMMAR_ENGINE_ENABLED)


def grammar_module_enabled() -> bool:
    settings = get_settings()
    return bool(grammar_engine_enabled()) and bool(
        getattr(settings, "LANG_GRAMMAR_MODULE_ENABLED", False)
    )
