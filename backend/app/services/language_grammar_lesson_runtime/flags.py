"""Feature flags for Grammar Lesson Runtime (G3.2)."""

from __future__ import annotations

from app.core.config import get_settings


def grammar_engine_enabled() -> bool:
    return bool(get_settings().LANG_GRAMMAR_ENGINE_ENABLED)


def grammar_engine_select_enabled() -> bool:
    return grammar_engine_enabled() and bool(get_settings().LANG_GRAMMAR_ENGINE_SELECT)
