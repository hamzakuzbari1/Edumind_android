"""Public API for the centralized Listening CEFR profile engine."""

from __future__ import annotations

from app.models.language.enums import LanguageLevel
from app.services.language_cefr.listening_profiles import LISTENING_CEFR_PROFILES
from app.services.language_cefr.types import (
    CEFR_LEVEL_CODES,
    CEFR_LEVELS,
    CefrListeningProfile,
    ListeningQuestionType,
    SentenceLimits,
    WordLimits,
)


class UnknownCefrLevelError(ValueError):
    """Raised when a CEFR level string or enum value is not registered."""


def normalize_cefr_level(level: str | LanguageLevel) -> LanguageLevel:
    """Normalize a level input to ``LanguageLevel``.

    Accepts enum members or case-insensitive codes (``\"a1\"`` → ``LanguageLevel.A1``).
    """
    if isinstance(level, LanguageLevel):
        return level
    key = (level or "").strip().upper()
    try:
        return LanguageLevel(key)
    except ValueError as exc:
        raise UnknownCefrLevelError(
            f"Unknown CEFR level {level!r}. Valid levels: {', '.join(CEFR_LEVEL_CODES)}"
        ) from exc


def validate_level_exists(level: str | LanguageLevel) -> bool:
    """Return ``True`` when ``level`` maps to a registered Listening profile."""
    try:
        normalize_cefr_level(level)
    except UnknownCefrLevelError:
        return False
    return True


def get_cefr_profile(level: str | LanguageLevel) -> CefrListeningProfile:
    """Return the complete immutable Listening profile for ``level``."""
    normalized = normalize_cefr_level(level)
    return LISTENING_CEFR_PROFILES[normalized]


def get_all_cefr_profiles() -> tuple[CefrListeningProfile, ...]:
    """Return all Listening profiles in ascending CEFR order."""
    return tuple(LISTENING_CEFR_PROFILES[level] for level in CEFR_LEVELS)


def get_allowed_question_types(level: str | LanguageLevel) -> tuple[ListeningQuestionType, ...]:
    """Return question types permitted at ``level``."""
    return get_cefr_profile(level).allowed_question_types


def get_forbidden_question_types(level: str | LanguageLevel) -> tuple[ListeningQuestionType, ...]:
    """Return question types forbidden at ``level``."""
    return get_cefr_profile(level).forbidden_question_types


def get_word_limits(level: str | LanguageLevel) -> WordLimits:
    """Return transcript word-count bounds for ``level``."""
    return get_cefr_profile(level).word_limits


def get_sentence_limits(level: str | LanguageLevel) -> SentenceLimits:
    """Return average sentence-length bounds for ``level``."""
    return get_cefr_profile(level).sentence_limits
