"""Runtime helpers for media storage provider selection (A6.0)."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.services.media_storage.constants import (
    DEFAULT_SIGNED_URL_TTL_SECONDS,
    MAX_SIGNED_URL_TTL_SECONDS,
    MIN_SIGNED_URL_TTL_SECONDS,
    PROVIDER_LOCAL,
    PROVIDER_SUPABASE,
)


def configured_media_provider(settings: Settings | None = None) -> str:
    s = settings or get_settings()
    raw = (getattr(s, "MEDIA_STORAGE_PROVIDER", None) or PROVIDER_LOCAL).strip().lower()
    if raw not in {PROVIDER_LOCAL, PROVIDER_SUPABASE}:
        return PROVIDER_LOCAL
    return raw


def supabase_configured(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    url = (getattr(s, "SUPABASE_URL", None) or "").strip()
    key = (getattr(s, "SUPABASE_SERVICE_ROLE_KEY", None) or "").strip()
    return bool(url and key)


def supabase_storage_enabled(settings: Settings | None = None) -> bool:
    """True only when provider is supabase AND credentials are present."""
    s = settings or get_settings()
    if configured_media_provider(s) != PROVIDER_SUPABASE:
        return False
    return supabase_configured(s)


def effective_storage_provider(settings: Settings | None = None) -> str:
    """Provider actually used for new writes — falls back to local when misconfigured."""
    s = settings or get_settings()
    if configured_media_provider(s) == PROVIDER_SUPABASE and supabase_configured(s):
        return PROVIDER_SUPABASE
    return PROVIDER_LOCAL


def signed_url_ttl_seconds(settings: Settings | None = None) -> int:
    s = settings or get_settings()
    raw = int(getattr(s, "SUPABASE_SIGNED_URL_TTL_SECONDS", DEFAULT_SIGNED_URL_TTL_SECONDS) or DEFAULT_SIGNED_URL_TTL_SECONDS)
    return max(MIN_SIGNED_URL_TTL_SECONDS, min(raw, MAX_SIGNED_URL_TTL_SECONDS))
