"""Centralized CEFR Profile Engine — Listening foundation (Phase 1.2).

This package is the single source of truth for Listening difficulty specifications.
Future phases will wire generation, validation, and audio realism to these profiles.

Do not import legacy ad-hoc word-count maps from generation services for new Listening work.
"""

from app.services.language_cefr.listening_runtime import (
    build_listening_cefr_profile_block,
    build_listening_generation_question_prompt_block,
    get_listening_generation_question_types,
    get_listening_generation_word_target,
    listening_generation_question_type_names,
    listening_prompt_spec_snapshot,
)
from app.services.language_cefr.listening_validator import (
    LISTENING_CEFR_MAX_ATTEMPTS,
    ListeningCefrValidationExhaustedError,
    ListeningValidationReport,
    validate_listening_lesson,
)
from app.services.language_cefr.engine import (
    UnknownCefrLevelError,
    get_all_cefr_profiles,
    get_allowed_question_types,
    get_cefr_profile,
    get_forbidden_question_types,
    get_sentence_limits,
    get_word_limits,
    normalize_cefr_level,
    validate_level_exists,
)
from app.services.language_cefr.transcript_format import (
    ListeningTranscriptFormat,
    classify_transcript_format,
    get_format_sentence_limits,
    is_multi_speaker_format,
)
from app.services.language_cefr.types import (
    CEFR_LEVEL_CODES,
    CEFR_LEVELS,
    CefrListeningProfile,
    ListeningQuestionType,
    SentenceLimits,
    WordLimits,
)

__all__ = (
    "CEFR_LEVEL_CODES",
    "CEFR_LEVELS",
    "CefrListeningProfile",
    "LISTENING_CEFR_MAX_ATTEMPTS",
    "ListeningCefrValidationExhaustedError",
    "ListeningQuestionType",
    "ListeningTranscriptFormat",
    "ListeningValidationReport",
    "SentenceLimits",
    "UnknownCefrLevelError",
    "WordLimits",
    "build_listening_cefr_profile_block",
    "build_listening_generation_question_prompt_block",
    "classify_transcript_format",
    "get_all_cefr_profiles",
    "get_allowed_question_types",
    "get_cefr_profile",
    "get_forbidden_question_types",
    "get_format_sentence_limits",
    "get_listening_generation_question_types",
    "get_listening_generation_word_target",
    "get_sentence_limits",
    "get_word_limits",
    "is_multi_speaker_format",
    "listening_generation_question_type_names",
    "listening_prompt_spec_snapshot",
    "normalize_cefr_level",
    "validate_level_exists",
    "validate_listening_lesson",
)
