"""Ephemeral OpenAI Realtime session minting for Speaking's live transcript preview.

MVP, display-only feature: lets the frontend show partial captions while the student is still
recording. This module NEVER touches grading -- the official transcript remains the backend's own
post-submit STT pipeline (language_transcription_service.transcribe_english_audio), called only
after the student clicks Submit. The ephemeral client secret minted here is scoped to
transcription only, expires in seconds, and is the only thing that ever reaches the browser --
settings.OPENAI_API_KEY (the real, long-lived key) is used solely for the outgoing request to
OpenAI and is never included in this module's return value or logs.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_REALTIME_CLIENT_SECRETS_URL = "https://api.openai.com/v1/realtime/client_secrets"


def live_transcription_enabled() -> bool:
    settings = get_settings()
    return (
        bool(settings.SPEAKING_LIVE_TRANSCRIPTION_ENABLED)
        and (settings.SPEAKING_LIVE_TRANSCRIPTION_PROVIDER or "").strip().lower() == "openai_realtime"
        and bool((settings.OPENAI_API_KEY or "").strip())
    )


async def create_live_transcription_session() -> dict | None:
    """Mint a short-lived ephemeral client secret scoped to transcription only.

    Returns None -- never raises -- if the feature is disabled, misconfigured, or the upstream
    call fails for any reason. Callers must treat None as "not available right now" and degrade
    the UI silently; a missing live preview is never an error worth surfacing to the student, and
    must never block recording, submission, grading, or section progression.
    """
    settings = get_settings()
    if not live_transcription_enabled():
        return None

    model = (settings.SPEAKING_LIVE_TRANSCRIPTION_MODEL or "gpt-realtime-whisper").strip()
    ttl_seconds = max(10, int(settings.SPEAKING_LIVE_TRANSCRIPTION_TOKEN_TTL_SECONDS or 60))

    payload = {
        "expires_after": {"anchor": "created_at", "seconds": ttl_seconds},
        "session": {
            "type": "transcription",
            "audio": {
                "input": {
                    "format": {"type": "audio/pcm", "rate": 24000},
                    # English-only placement exam (matches the official post-submit STT pipeline's
                    # own hardcoded language="en" in language_transcription_service.py) -- without
                    # this hint the model sometimes guesses a spoken name's script (e.g. Arabic)
                    # instead of transliterating it, which looks broken in an English exam preview.
                    "transcription": {"model": model, "language": "en"},
                }
            },
        },
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            response = await client.post(
                _REALTIME_CLIENT_SECRETS_URL,
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if response.status_code >= 400:
            logger.warning("Live transcription session creation failed status=%s", response.status_code)
            return None
        data = response.json()
    except Exception as exc:
        logger.warning("Live transcription session creation failed error_type=%s", type(exc).__name__)
        return None

    # Defensive: OpenAI's Realtime session-creation response has carried the ephemeral value both
    # at the top level and nested under "client_secret" across API iterations -- accept either
    # shape rather than assuming one, so a minor upstream shape change degrades to "unavailable"
    # instead of raising.
    nested = data.get("client_secret") if isinstance(data.get("client_secret"), dict) else {}
    client_secret = data.get("value") or nested.get("value")
    expires_at = data.get("expires_at") or nested.get("expires_at")
    if not client_secret:
        logger.warning("Live transcription session response missing an ephemeral client secret value")
        return None

    return {
        "client_secret": str(client_secret),
        "expires_at": int(expires_at) if isinstance(expires_at, (int, float)) else None,
        "model": model,
    }
