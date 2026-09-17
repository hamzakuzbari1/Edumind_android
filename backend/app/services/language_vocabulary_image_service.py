"""Vocabulary word illustrations — Gemini native image generation.

Generated on-demand (one card at a time, never eagerly for a whole batch) and cached on the
LanguageContentItem itself (body_json.image_url), so a word is only ever generated once across
every student who ever sees it.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.models.language.content import LanguageContentItem

logger = logging.getLogger(__name__)
settings = get_settings()

_GEMINI_GENERATE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Gemini's image model returns 503 ("high demand... usually temporary") often enough in practice
# that a couple of short retries meaningfully improves the success rate — Google's own error
# message says to just try again.
_RETRYABLE_STATUS = {503}
_RETRY_DELAYS_SECONDS = (1.5, 3.0)


async def get_or_create_word_image(db: AsyncSession, *, content_id: int) -> str | None:
    """Return a cached image URL for this vocabulary word, generating it once if missing."""
    item = await db.get(LanguageContentItem, content_id)
    if not item:
        return None
    body = item.body_json or {}
    cached = body.get("image_url")
    if cached:
        return cached
    if not settings.ENABLE_VOCABULARY_IMAGES or not settings.GEMINI_API_KEY:
        return None

    prompt = str(body.get("image_prompt") or item.title or "").strip()
    if not prompt:
        return None

    url = await _generate_image_gemini(prompt)
    if not url:
        return None

    body["image_url"] = url
    item.body_json = body
    flag_modified(item, "body_json")
    await db.commit()
    return url


async def _generate_image_gemini(prompt: str) -> str | None:
    api_key = (settings.GEMINI_API_KEY or "").strip()
    if not api_key:
        return None
    model = (settings.LANGUAGE_VOCABULARY_IMAGE_MODEL or "gemini-2.5-flash-image").strip()

    request_prompt = (
        "Generate a single simple, clear, friendly illustration for an English vocabulary "
        "flashcard. Absolutely no text, words, letters, numbers, labels, or signs anywhere in the "
        f"image — a pure visual scene only. Scene: {prompt}"
    )
    attempts = len(_RETRY_DELAYS_SECONDS) + 1
    response = None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            for attempt in range(attempts):
                last_attempt = attempt == attempts - 1
                try:
                    response = await client.post(
                        _GEMINI_GENERATE_URL.format(model=model),
                        params={"key": api_key},
                        json={
                            "contents": [{"parts": [{"text": request_prompt}]}],
                            "generationConfig": {"responseModalities": ["IMAGE"]},
                        },
                    )
                except httpx.TransportError as exc:
                    # DNS blips / connection resets are just as transient as a 503 — same retry.
                    if last_attempt:
                        raise
                    logger.info(
                        "Gemini image generation network error (attempt %d/%d): %s — retrying in %.1fs",
                        attempt + 1, attempts, exc, _RETRY_DELAYS_SECONDS[attempt],
                    )
                    await asyncio.sleep(_RETRY_DELAYS_SECONDS[attempt])
                    continue
                if response.status_code not in _RETRYABLE_STATUS or last_attempt:
                    break
                logger.info(
                    "Gemini image generation got %s (attempt %d/%d) — retrying in %.1fs",
                    response.status_code, attempt + 1, attempts, _RETRY_DELAYS_SECONDS[attempt],
                )
                await asyncio.sleep(_RETRY_DELAYS_SECONDS[attempt])
        if response.status_code >= 400:
            logger.warning(
                "Gemini image generation failed: status=%s detail=%s",
                response.status_code, response.text[:300],
            )
            return None
        payload = response.json()
    except Exception as exc:  # pragma: no cover - network/provider variance
        logger.warning("Gemini image generation errored: %s", exc)
        return None

    image_b64 = _extract_inline_image(payload)
    if not image_b64:
        return None

    out_dir = Path(settings.UPLOAD_DIR) / "vocabulary_images"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{uuid.uuid4().hex}.png"
    try:
        dest.write_bytes(base64.b64decode(image_b64))
    except Exception as exc:  # pragma: no cover - disk/encoding variance
        logger.warning("Could not write generated vocabulary image: %s", exc)
        return None

    rel = dest.resolve().relative_to(Path(settings.UPLOAD_DIR).resolve())
    return "/uploads/" + "/".join(rel.parts)


def _extract_inline_image(payload: dict) -> str | None:
    try:
        for candidate in payload.get("candidates") or []:
            parts = ((candidate.get("content") or {}).get("parts")) or []
            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return inline["data"]
    except Exception:  # pragma: no cover - defensive against provider shape drift
        return None
    return None
