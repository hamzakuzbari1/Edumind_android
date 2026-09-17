"""Feature flags for Grammar Progression (G2.1)."""

from __future__ import annotations

from app.core.config import get_settings


def grammar_engine_enabled() -> bool:
    """Core Grammar spine gate — Progression compute/persist requires this."""
    return bool(get_settings().LANG_GRAMMAR_ENGINE_ENABLED)


def grammar_engine_select_enabled() -> bool:
    """Selection authority gate — current/next may be consumed by skills only when both flags are on."""
    return grammar_engine_enabled() and bool(get_settings().LANG_GRAMMAR_ENGINE_SELECT)
