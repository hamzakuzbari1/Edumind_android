"""Stable prosody/delivery issue tags (S6) — no subjective diagnostic tags."""

from __future__ import annotations

ISSUE_LOW_PITCH_VARIATION = "prosody:low_pitch_variation"
ISSUE_HIGH_PITCH_INSTABILITY = "prosody:high_pitch_instability"
ISSUE_MONOTONE_DELIVERY = "prosody:monotone_delivery"
ISSUE_FREQUENT_LONG_PAUSES = "prosody:frequent_long_pauses"
ISSUE_HIGH_PAUSE_DENSITY = "prosody:high_pause_density"
ISSUE_UNSTABLE_SPEAKING_RATE = "prosody:unstable_speaking_rate"
ISSUE_LOW_ENERGY_VARIATION = "prosody:low_energy_variation"
ISSUE_QUESTION_INTONATION_FLAT = "prosody:question_intonation_flat"
ISSUE_TERMINAL_INTONATION_MISMATCH = "prosody:terminal_intonation_mismatch"
ISSUE_FREQUENT_HESITATION = "delivery:frequent_hesitation"
ISSUE_FRAGMENTED_RHYTHM = "delivery:fragmented_rhythm"

ALL_PROSODY_ISSUE_TAGS: frozenset[str] = frozenset(
    {
        ISSUE_LOW_PITCH_VARIATION,
        ISSUE_HIGH_PITCH_INSTABILITY,
        ISSUE_MONOTONE_DELIVERY,
        ISSUE_FREQUENT_LONG_PAUSES,
        ISSUE_HIGH_PAUSE_DENSITY,
        ISSUE_UNSTABLE_SPEAKING_RATE,
        ISSUE_LOW_ENERGY_VARIATION,
        ISSUE_QUESTION_INTONATION_FLAT,
        ISSUE_TERMINAL_INTONATION_MISMATCH,
        ISSUE_FREQUENT_HESITATION,
        ISSUE_FRAGMENTED_RHYTHM,
    }
)
