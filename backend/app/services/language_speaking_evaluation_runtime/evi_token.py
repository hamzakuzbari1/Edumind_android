"""Hume EVI token minting (server-side only — never expose secret to browser)."""

from __future__ import annotations

import base64

import httpx

from app.core.config import get_settings
from app.services.language_speaking_live_conversation.errors import (
    LiveAuthenticationFailedError,
    LiveConfigurationInvalidError,
)

_HUME_TOKEN_URL = "https://api.hume.ai/oauth2-cc/token"


def mint_evi_access_token(*, ttl_hint_seconds: int | None = None) -> dict[str, object]:
    settings = get_settings()
    api_key = (settings.HUME_API_KEY or "").strip()
    secret = (settings.HUME_SECRET_KEY or "").strip()
    if not api_key or not secret:
        raise LiveConfigurationInvalidError(
            "HUME_API_KEY and HUME_SECRET_KEY required for EVI access token",
            detail="missing_credentials",
        )
    basic = base64.b64encode(f"{api_key}:{secret}".encode()).decode()
    ttl = ttl_hint_seconds or int(settings.SPEAKING_EVI_TOKEN_TTL_SECONDS or 1500)
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            _HUME_TOKEN_URL,
            headers={"Authorization": f"Basic {basic}"},
            data={"grant_type": "client_credentials"},
        )
    if resp.status_code == 401:
        raise LiveAuthenticationFailedError("Hume token authentication failed")
    if resp.status_code >= 400:
        raise LiveAuthenticationFailedError(
            "Hume token request failed",
            detail=f"status={resp.status_code}",
        )
    body = resp.json()
    token = str(body.get("access_token") or "")
    if not token:
        raise LiveAuthenticationFailedError("Hume token response missing access_token")
    expires_in = int(body.get("expires_in") or ttl)
    config_id = (settings.HUME_EVI_CONFIG_ID or "").strip()
    if not config_id:
        raise LiveConfigurationInvalidError("HUME_EVI_CONFIG_ID is not configured")
    return {
        "access_token": token,
        "expires_in": expires_in,
        "config_id": config_id,
        "token_type": str(body.get("token_type") or "Bearer"),
        "provider": "hume_evi",
        "api_version": "v0",
    }
