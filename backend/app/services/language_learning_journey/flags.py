"""Flags for Learning Journey projection — reuse grammar engine gate."""

from __future__ import annotations

from app.core.config import get_settings


def learning_journey_enabled() -> bool:
    return bool(get_settings().LANG_GRAMMAR_ENGINE_ENABLED)
