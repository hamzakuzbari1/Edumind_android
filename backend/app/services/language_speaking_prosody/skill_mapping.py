"""Deterministic S1 skill ID mapping from prosody issue tags (S6)."""

from __future__ import annotations

from app.services.language_speaking_prosody.issue_taxonomy import (
    ISSUE_FRAGMENTED_RHYTHM,
    ISSUE_FREQUENT_HESITATION,
    ISSUE_FREQUENT_LONG_PAUSES,
    ISSUE_HIGH_PAUSE_DENSITY,
    ISSUE_LOW_ENERGY_VARIATION,
    ISSUE_LOW_PITCH_VARIATION,
    ISSUE_MONOTONE_DELIVERY,
    ISSUE_QUESTION_INTONATION_FLAT,
    ISSUE_TERMINAL_INTONATION_MISMATCH,
    ISSUE_UNSTABLE_SPEAKING_RATE,
)

_VALID_SKILL_IDS: frozenset[str] = frozenset(
    {
        "prosody:question_intonation",
        "prosody:sentence_stress",
        "prosody:intonation_contours",
        "prosody:polar_question_rhythm",
        "prosody:wh_question_fall",
        "prosody:thought_groups",
        "prosody:emphasis_contrast",
        "fluency:appropriate_rate",
        "fluency:pause_control",
        "fluency:response_timing",
        "fluency:extended_speech",
        "fluency:ielts_time_pressure",
        "fluency:filler_reduction",
    }
)

_ISSUE_SKILL_MAP: dict[str, tuple[str, ...]] = {
    ISSUE_LOW_PITCH_VARIATION: ("prosody:sentence_stress", "prosody:emphasis_contrast"),
    ISSUE_MONOTONE_DELIVERY: ("prosody:sentence_stress", "prosody:emphasis_contrast"),
    ISSUE_QUESTION_INTONATION_FLAT: ("prosody:question_intonation",),
    ISSUE_TERMINAL_INTONATION_MISMATCH: ("prosody:intonation_contours",),
    ISSUE_FREQUENT_HESITATION: ("fluency:pause_control", "fluency:filler_reduction"),
    ISSUE_FREQUENT_LONG_PAUSES: ("fluency:pause_control",),
    ISSUE_HIGH_PAUSE_DENSITY: ("fluency:pause_control",),
    ISSUE_UNSTABLE_SPEAKING_RATE: ("fluency:appropriate_rate",),
    ISSUE_FRAGMENTED_RHYTHM: ("fluency:appropriate_rate", "prosody:thought_groups"),
    ISSUE_LOW_ENERGY_VARIATION: ("prosody:emphasis_contrast",),
}


def candidate_skills_for_issue(issue_tag: str) -> tuple[str, ...]:
    raw = _ISSUE_SKILL_MAP.get(issue_tag, ())
    return tuple(sid for sid in raw if sid in _VALID_SKILL_IDS)
