"""Types for the centralized Listening CEFR profile engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.models.language.enums import LanguageLevel


class ListeningQuestionType(StrEnum):
    """Canonical listening question types for CEFR blueprint alignment."""

    detail = "detail"
    main_idea = "main_idea"
    inference = "inference"
    speaker_intention = "speaker_intention"
    opinion = "opinion"
    tone = "tone"
    bias = "bias"
    purpose = "purpose"
    prediction = "prediction"
    matching = "matching"
    sequence = "sequence"
    true_false_notgiven = "true_false_notgiven"
    sentence_completion = "sentence_completion"


# Ordered CEFR ladder — single registry for Listening profile lookups.
CEFR_LEVELS: tuple[LanguageLevel, ...] = (
    LanguageLevel.A1,
    LanguageLevel.A2,
    LanguageLevel.B1,
    LanguageLevel.B2,
    LanguageLevel.C1,
    LanguageLevel.C2,
)

CEFR_LEVEL_CODES: tuple[str, ...] = tuple(level.value for level in CEFR_LEVELS)


@dataclass(frozen=True, slots=True)
class WordLimits:
    """Transcript word-count bounds for a CEFR level."""

    min_words: int
    ideal_words: int
    max_words: int


@dataclass(frozen=True, slots=True)
class SentenceLimits:
    """Average sentence length bounds (words per sentence)."""

    min_words: int
    max_words: int


@dataclass(frozen=True, slots=True)
class CefrListeningProfile:
    """Immutable Listening difficulty specification for one CEFR level.

    Source of truth: LANGUAGE-CEFR-BLUEPRINT (Phase 1.1). Future Listening
    generation, validation, and audio realism phases must consume this profile
    instead of ad-hoc constants.
    """

    level: LanguageLevel
    transcript_min_words: int
    transcript_max_words: int
    ideal_word_count: int
    sentence_min_words: int
    sentence_max_words: int
    allowed_grammar: tuple[str, ...]
    forbidden_grammar: tuple[str, ...]
    vocabulary_band: str
    topic_complexity: str
    listening_objectives: tuple[str, ...]
    allowed_question_types: tuple[ListeningQuestionType, ...]
    forbidden_question_types: tuple[ListeningQuestionType, ...]
    distractor_complexity: str
    inference_level: str
    cognitive_load: str
    recommended_speaking_speed: str
    recommended_accent: str
    learning_goal: str

    @property
    def word_limits(self) -> WordLimits:
        return WordLimits(
            min_words=self.transcript_min_words,
            ideal_words=self.ideal_word_count,
            max_words=self.transcript_max_words,
        )

    @property
    def sentence_limits(self) -> SentenceLimits:
        return SentenceLimits(
            min_words=self.sentence_min_words,
            max_words=self.sentence_max_words,
        )
