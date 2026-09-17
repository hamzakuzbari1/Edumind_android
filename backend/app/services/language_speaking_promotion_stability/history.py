"""Rolling readiness history helpers for speaking promotion stability."""

from __future__ import annotations

from app.services.language_speaking_promotion_stability.policy import SpeakingStabilityPolicy
from app.services.language_speaking_promotion_stability.types import SpeakingReadinessHistoryEntry


def append_history_entry(
    history: list[SpeakingReadinessHistoryEntry],
    entry: SpeakingReadinessHistoryEntry,
    *,
    policy: SpeakingStabilityPolicy,
) -> list[SpeakingReadinessHistoryEntry]:
    """Dedup by signal fingerprint — same evidence must not inflate history."""
    updated = [e for e in history if e.signal_fingerprint != entry.signal_fingerprint]
    updated.append(entry)
    if len(updated) > policy.max_history_entries:
        updated = updated[-policy.max_history_entries :]
    return updated


def windowed(
    history: list[SpeakingReadinessHistoryEntry],
    *,
    policy: SpeakingStabilityPolicy,
) -> list[SpeakingReadinessHistoryEntry]:
    return history[-policy.rolling_window :] if history else []


def consecutive_high_scores(
    history: list[SpeakingReadinessHistoryEntry],
    *,
    policy: SpeakingStabilityPolicy,
) -> int:
    streak = 0
    for entry in reversed(history):
        if entry.readiness_score >= policy.high_score_threshold and entry.hard_blockers_empty:
            streak += 1
        else:
            break
    return streak
