"""Feature flags for Grammar Speaking Domain (V1.2A)."""

from __future__ import annotations

from app.core.config import get_settings


def grammar_engine_enabled() -> bool:
    return bool(get_settings().LANG_GRAMMAR_ENGINE_ENABLED)


def speaking_domain_enabled() -> bool:
    """Domain models are always importable; flag gates future runtime use."""
    settings = get_settings()
    return bool(settings.LANG_GRAMMAR_ENGINE_ENABLED) and bool(
        getattr(settings, "LANG_GRAMMAR_SPEAKING_DOMAIN_ENABLED", True)
    )
