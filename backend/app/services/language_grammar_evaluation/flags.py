"""Feature flags for Grammar-Constrained Evaluation (V1.8)."""

from __future__ import annotations

from app.core.config import get_settings


def grammar_engine_enabled() -> bool:
    return bool(get_settings().LANG_GRAMMAR_ENGINE_ENABLED)


def grammar_evaluation_enabled() -> bool:
    settings = get_settings()
    return bool(grammar_engine_enabled()) and bool(
        getattr(settings, "LANG_GRAMMAR_EVALUATION_ENABLED", True)
    )


def grammar_evaluation_strict() -> bool:
    return bool(getattr(get_settings(), "LANG_GRAMMAR_EVALUATION_STRICT", True))
