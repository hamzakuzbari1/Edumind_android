"""Resolve Deepgram language codes from server-owned lesson metadata."""

from __future__ import annotations

from app.core.config import get_settings

# Explicit locale / language aliases → Deepgram language codes.
_LOCALE_MAP: dict[str, str] = {
    "ar-sy": "ar-SY",
    "ar_sy": "ar-SY",
    "arsy": "ar-SY",
    "sy": "ar-SY",
    "syr": "ar-SY",
    "syria": "ar-SY",
    "syrian": "ar-SY",
    "ar": "ar",
    "arabic": "ar",
    "en": "en",
    "en-us": "en",
    "en_us": "en",
    "en-gb": "en",
    "en_gb": "en",
    "english": "en",
}


def map_locale_to_deepgram_language(locale: str | None) -> str | None:
    """Map a known locale/language token to a Deepgram language code."""
    if not locale:
        return None
    token = (locale or "").strip().lower().replace(" ", "")
    if not token:
        return None
    # Try both underscore and hyphen forms.
    for candidate in (token, token.replace("-", "_"), token.replace("_", "-")):
        mapped = _LOCALE_MAP.get(candidate)
        if mapped:
            return mapped
    # Bare BCP-47 prefixes: ar-SY already handled; ar-XX → ar, en-XX → en
    if token.startswith("ar-sy") or token.startswith("ar_sy"):
        return "ar-SY"
    if token == "ar" or token.startswith("ar-") or token.startswith("ar_"):
        return "ar"
    if token == "en" or token.startswith("en-") or token.startswith("en_"):
        return "en"
    return None


def resolve_video_transcription_language(
    *,
    locale: str | None = None,
    language_hint: str | None = None,
    subject: str | None = None,
) -> str:
    """Resolve STT language from metadata; never blind auto-detect.

    Priority:
    1. explicit ``language_hint`` / ``locale`` when mappable
    2. subject heuristics for English lessons only
    3. configured ``DEEPGRAM_STT_LANGUAGE`` (default ar-SY)
    4. ``LESSON_VIDEO_WHISPER_LANGUAGE`` mapped if present
    """
    settings = get_settings()

    for candidate in (language_hint, locale):
        mapped = map_locale_to_deepgram_language(candidate)
        if mapped:
            return mapped

    subject_l = (subject or "").strip().lower()
    if subject_l in {"english", "en", "لغة إنجليزية", "الانجليزية", "الإنجليزية", "english language"}:
        return "en"
    if subject_l in {"arabic", "ar", "لغة عربية", "العربية", "arabic language"}:
        return "ar"

    configured = (settings.DEEPGRAM_STT_LANGUAGE or "").strip()
    mapped_cfg = map_locale_to_deepgram_language(configured) or (
        configured if configured in {"ar-SY", "ar", "en"} else None
    )
    if mapped_cfg:
        return mapped_cfg

    whisper_lang = map_locale_to_deepgram_language(settings.LESSON_VIDEO_WHISPER_LANGUAGE)
    if whisper_lang:
        return whisper_lang

    return "ar-SY"
