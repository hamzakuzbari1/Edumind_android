"""Stable pronunciation issue tags (S5) — no prose mistake IDs."""

from __future__ import annotations

# Canonical issue tag strings — persisted as stable identifiers.
ISSUE_THETA_TO_S = "pronunciation:theta_to_s"
ISSUE_THETA_TO_T = "pronunciation:theta_to_t"
ISSUE_ETH_TO_D = "pronunciation:eth_to_d"
ISSUE_FINAL_CONSONANT_OMISSION = "pronunciation:final_consonant_omission"
ISSUE_VOWEL_REDUCTION = "pronunciation:vowel_reduction"
ISSUE_WORD_STRESS = "pronunciation:word_stress"
ISSUE_CONSONANT_CLUSTER_REDUCTION = "pronunciation:consonant_cluster_reduction"

ALL_PRONUNCIATION_ISSUE_TAGS: frozenset[str] = frozenset(
    {
        ISSUE_THETA_TO_S,
        ISSUE_THETA_TO_T,
        ISSUE_ETH_TO_D,
        ISSUE_FINAL_CONSONANT_OMISSION,
        ISSUE_VOWEL_REDUCTION,
        ISSUE_WORD_STRESS,
        ISSUE_CONSONANT_CLUSTER_REDUCTION,
    }
)

# Normalized IPA symbols for comparison (espeak-style).
_THETA_SYMBOLS = frozenset({"θ", "T"})
_ETH_SYMBOLS = frozenset({"ð", "D"})
_S_SYMBOLS = frozenset({"s", "S"})
_T_SYMBOLS = frozenset({"t", "T"})


def classify_phoneme_substitution(expected: str, observed: str) -> str | None:
    """Return a stable issue tag for a phoneme substitution, or None if unclassified."""
    exp = (expected or "").strip()
    obs = (observed or "").strip()
    if not exp or not obs or exp == obs:
        return None
    if exp in _THETA_SYMBOLS and obs in _S_SYMBOLS:
        return ISSUE_THETA_TO_S
    if exp in _THETA_SYMBOLS and obs in _T_SYMBOLS:
        return ISSUE_THETA_TO_T
    if exp in _ETH_SYMBOLS and obs in {"d", "D", "z", "Z"}:
        return ISSUE_ETH_TO_D
    return None


def classify_phoneme_omission(expected: str, observed: str, *, word_final: bool = False) -> str | None:
    """Return a stable issue tag for a phoneme omission."""
    exp = (expected or "").strip()
    obs = (observed or "").strip()
    if exp and not obs:
        if word_final and exp not in {"ə", "@", "ɚ", "r"}:
            return ISSUE_FINAL_CONSONANT_OMISSION
        return ISSUE_VOWEL_REDUCTION
    return None
