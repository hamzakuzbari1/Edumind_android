"""Feature flags for Grammar Activity Providers (G3.3)."""

from __future__ import annotations

from app.core.config import get_settings
from app.services.language_grammar_activity_provider.types import GrammarActivityProviderId


def grammar_engine_enabled() -> bool:
    return bool(get_settings().LANG_GRAMMAR_ENGINE_ENABLED)


def configured_provider_id() -> GrammarActivityProviderId:
    """Deterministic provider id from settings (invalid values fall back to template)."""
    raw = str(get_settings().LANG_GRAMMAR_ACTIVITY_PROVIDER or "template").strip().lower()
    try:
        return GrammarActivityProviderId(raw)
    except ValueError:
        return GrammarActivityProviderId.template
