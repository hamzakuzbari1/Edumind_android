"""Supertonic voice configuration for listening TTS (gender-aware)."""

from __future__ import annotations

from app.core.config import get_settings

FemaleGender = "female"
MaleGender = "male"


def default_voice() -> str:
    settings = get_settings()
    return (settings.LANGUAGE_SUPERTONIC_VOICE_FEMALE or settings.LANGUAGE_SUPERTONIC_VOICE or "F1").strip() or "F1"


def female_voice() -> str:
    settings = get_settings()
    return (settings.LANGUAGE_SUPERTONIC_VOICE_FEMALE or "F1").strip() or "F1"


def male_voice() -> str:
    settings = get_settings()
    return (settings.LANGUAGE_SUPERTONIC_VOICE_MALE or "M1").strip() or "M1"


def normalize_gender(raw: str | None) -> str | None:
    if not raw:
        return None
    value = str(raw).strip().lower()
    if value in ("female", "f", "woman", "girl"):
        return FemaleGender
    if value in ("male", "m", "man", "boy"):
        return MaleGender
    return None


def voice_for_gender(gender: str | None) -> str:
    normalized = normalize_gender(gender)
    if normalized == FemaleGender:
        return female_voice()
    if normalized == MaleGender:
        return male_voice()
    return default_voice()
