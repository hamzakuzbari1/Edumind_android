"""Listening runtime helpers — generation reads full CEFR profiles (Phase 1.4+)."""

from __future__ import annotations

from app.models.language.enums import LanguageLevel
from app.services.language_cefr.engine import get_cefr_profile
from app.services.language_cefr.types import CefrListeningProfile, ListeningQuestionType

_QUESTION_TYPE_INSTRUCTIONS: dict[ListeningQuestionType, str] = {
    ListeningQuestionType.main_idea: (
        "main_idea — identify the overall point; 4 choices, exactly one correct."
    ),
    ListeningQuestionType.detail: (
        "detail — locate an explicit fact from the transcript; 4 choices, exactly one correct."
    ),
    ListeningQuestionType.inference: (
        "inference — one logical step beyond what is stated; 4 choices, exactly one correct."
    ),
    ListeningQuestionType.speaker_intention: (
        "speaker_intention — why the speaker says or does something; 4 choices, exactly one correct."
    ),
    ListeningQuestionType.opinion: (
        "opinion — identify a stated view; 4 choices, exactly one correct."
    ),
    ListeningQuestionType.tone: (
        "tone — identify speaker attitude (e.g. friendly, annoyed); 4 choices, exactly one correct."
    ),
    ListeningQuestionType.bias: (
        "bias — identify stance, framing, or slant; 4 choices, exactly one correct."
    ),
    ListeningQuestionType.purpose: (
        "purpose — why the talk, message, or announcement exists; 4 choices, exactly one correct."
    ),
    ListeningQuestionType.prediction: (
        "prediction — what happens or is said next; 4 choices, exactly one correct."
    ),
    ListeningQuestionType.true_false_notgiven: (
        'true_false_notgiven — choices MUST be EXACTLY ["True","False","Not Given"].'
    ),
    ListeningQuestionType.sentence_completion: (
        "sentence_completion — sentence about what was said with ONE blank '_____' + 4 options."
    ),
    ListeningQuestionType.matching: (
        "matching — pair a name, place, or item with a fact (present as 4 choices, one correct pairing)."
    ),
    ListeningQuestionType.sequence: (
        "sequence — order events or steps (present as 4 choices for the correct order or next step)."
    ),
}


def get_listening_generation_word_target(level: str | LanguageLevel) -> int:
    """Transcript ideal word target (convenience wrapper)."""
    return get_cefr_profile(level).ideal_word_count


def get_listening_generation_question_types(
    level: str | LanguageLevel,
) -> tuple[ListeningQuestionType, ...]:
    """Question types permitted for listening generation at ``level``."""
    return get_cefr_profile(level).allowed_question_types


def listening_generation_question_type_names(
    types: tuple[ListeningQuestionType, ...] | None = None,
    *,
    level: str | LanguageLevel | None = None,
) -> tuple[str, ...]:
    """Stable string names for JSON schema / stored question ``type`` fields."""
    if types is not None:
        source = types
    elif level is not None:
        source = get_listening_generation_question_types(level)
    else:
        raise ValueError("Provide types or level")
    return tuple(t.value for t in source)


def _bullet_lines(items: tuple[str, ...], *, prefix: str = "- ") -> str:
    if not items:
        return f"{prefix}(none)"
    return "\n".join(f"{prefix}{item}" for item in items)


def build_listening_cefr_profile_block(level: str | LanguageLevel) -> str:
    """Render the [CEFR PROFILE] instruction block from the centralized engine."""
    profile = get_cefr_profile(level)
    wl = profile.word_limits
    sl = profile.sentence_limits
    forbidden_grammar = profile.forbidden_grammar or ("(none)",)
    forbidden_questions = profile.forbidden_question_types

    return (
        "[CEFR PROFILE]\n"
        f"Target Level: {profile.level.value}\n\n"
        "Transcript:\n"
        f"- Word count: {wl.min_words}–{wl.max_words} words (ideal ~{wl.ideal_words})\n"
        f"- Average sentence length: {sl.min_words}–{sl.max_words} words per sentence\n"
        f"- Recommended speaking speed: {profile.recommended_speaking_speed}\n"
        f"- Recommended accent: {profile.recommended_accent}\n\n"
        "Grammar:\n"
        f"- Allowed:\n{_bullet_lines(profile.allowed_grammar, prefix='  • ')}\n"
        f"- Forbidden (must NOT appear in the transcript):\n"
        f"{_bullet_lines(forbidden_grammar, prefix='  • ')}\n\n"
        f"Vocabulary:\n{profile.vocabulary_band}\n\n"
        f"Topic Complexity:\n{profile.topic_complexity}\n\n"
        "Listening Objectives:\n"
        f"{_bullet_lines(profile.listening_objectives)}\n\n"
        "Question Types:\n"
        f"- Allowed ONLY: {', '.join(t.value for t in profile.allowed_question_types)}\n"
        f"- Forbidden (never generate): "
        f"{', '.join(t.value for t in forbidden_questions) if forbidden_questions else 'none'}\n\n"
        f"Distractor Difficulty:\n{profile.distractor_complexity}\n\n"
        f"Learning Objective:\n{profile.learning_goal}\n"
        "[/CEFR PROFILE]"
    )


def _question_instructions_for_profile(profile: CefrListeningProfile) -> list[str]:
    lines: list[str] = []
    for qtype in profile.allowed_question_types:
        instruction = _QUESTION_TYPE_INSTRUCTIONS.get(qtype)
        if instruction:
            lines.append(f"- {instruction}")
    return lines


def build_listening_generation_question_prompt_block(
    level: str | LanguageLevel,
) -> str:
    """Question-generation instructions derived from the CEFR profile."""
    profile = get_cefr_profile(level)
    allowed = profile.allowed_question_types
    if not allowed:
        raise ValueError(f"No allowed question types for CEFR level {profile.level.value}")

    type_union = " | ".join(t.value for t in allowed)
    instruction_lines = _question_instructions_for_profile(profile)
    forbidden = profile.forbidden_question_types
    forbidden_line = (
        f"NEVER use these question types: {', '.join(t.value for t in forbidden)}. "
        if forbidden
        else ""
    )
    mix_hint = (
        f"Draw every question type from the allowed list only "
        f"({', '.join(t.value for t in allowed)}). "
        f"Use at least {min(3, len(allowed))} different allowed types across the four questions when possible. "
    )

    return (
        "exactly 4 questions:\n"
        + "\n".join(instruction_lines)
        + "\n"
        + mix_hint
        + forbidden_line
        + "For each question add a short English explanation, and evidence_quote = an EXACT substring "
        "from the transcript ('' for Not Given). "
        "When audio_transcript uses speaker labels (e.g. 'Sarah:', 'John:'), include a speakers array: "
        '[{"id":"speaker_1","name":"Sarah","gender":"female"}, ...] with one entry per distinct label; '
        'gender must be "female" or "male". For single-speaker monologues without labels, omit speakers '
        "or include one speaker entry. "
        f'Return ONLY JSON: {{"items":[{{"title": str, "audio_transcript": str, '
        f'"instructions": short English listening instruction, '
        f'"speakers": optional list of {{"id": str, "name": str, "gender": "female"|"male"}}, '
        f'"questions":[{{"stem": str, "choices":[2-4 strings], "correct_index": int, '
        f'"type": "{type_union}", '
        f'"explanation": str, "evidence_quote": str}}]}}]}}'
    )


def listening_prompt_spec_snapshot(level: str | LanguageLevel) -> dict[str, object]:
    """Structured snapshot of generation constraints — used by verification scripts."""
    profile = get_cefr_profile(level)
    wl = profile.word_limits
    sl = profile.sentence_limits
    return {
        "level": profile.level.value,
        "word_min": wl.min_words,
        "word_ideal": wl.ideal_words,
        "word_max": wl.max_words,
        "sentence_min": sl.min_words,
        "sentence_max": sl.max_words,
        "allowed_grammar": profile.allowed_grammar,
        "forbidden_grammar": profile.forbidden_grammar,
        "vocabulary_band": profile.vocabulary_band,
        "topic_complexity": profile.topic_complexity,
        "listening_objectives": profile.listening_objectives,
        "allowed_question_types": tuple(t.value for t in profile.allowed_question_types),
        "forbidden_question_types": tuple(t.value for t in profile.forbidden_question_types),
        "learning_goal": profile.learning_goal,
    }
