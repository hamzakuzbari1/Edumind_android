"""Deterministic S1 skill ID mapping from pronunciation issue tags (S5)."""

from __future__ import annotations

from app.services.language_speaking_pronunciation.issue_taxonomy import (
    ISSUE_CONSONANT_CLUSTER_REDUCTION,
    ISSUE_ETH_TO_D,
    ISSUE_FINAL_CONSONANT_OMISSION,
    ISSUE_THETA_TO_S,
    ISSUE_THETA_TO_T,
    ISSUE_VOWEL_REDUCTION,
    ISSUE_WORD_STRESS,
)

# Known S1 phoneme/pattern node IDs (verified in S1 catalog — no curriculum import here).
_VALID_SKILL_IDS: frozenset[str] = frozenset(
    {
        "phoneme:theta",
        "phoneme:eth",
        "phoneme:short_i",
        "phoneme:ed_endings",
        "pattern:th_substitution",
        "pattern:vowel_length",
        "pattern:word_stress",
        "pattern:schwa_unstressed",
        "pattern:linking_sounds",
        "pattern:connected_th",
        "pattern:theta_phrase_drill",
        "word:think",
        "word:three",
    }
)

_ISSUE_SKILL_MAP: dict[str, tuple[str, ...]] = {
    ISSUE_THETA_TO_S: ("phoneme:theta", "pattern:th_substitution"),
    ISSUE_THETA_TO_T: ("phoneme:theta", "pattern:th_substitution"),
    ISSUE_ETH_TO_D: ("phoneme:eth",),
    ISSUE_FINAL_CONSONANT_OMISSION: ("phoneme:theta", "pattern:th_substitution"),
    ISSUE_VOWEL_REDUCTION: ("phoneme:short_i", "pattern:vowel_length"),
    ISSUE_WORD_STRESS: ("pattern:word_stress",),
    ISSUE_CONSONANT_CLUSTER_REDUCTION: ("pattern:th_substitution",),
}


def candidate_skills_for_issue(issue_tag: str) -> tuple[str, ...]:
    """Return candidate S1 skill IDs only when mapping is deterministic and nodes exist."""
    raw = _ISSUE_SKILL_MAP.get(issue_tag, ())
    return tuple(sid for sid in raw if sid in _VALID_SKILL_IDS)
