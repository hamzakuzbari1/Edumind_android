"""Challenge promotion/demotion with hysteresis (Phase 3.3)."""

from __future__ import annotations

from app.services.language_listening_challenge.constants import (
    CHALLENGE_LEVEL_ORDER,
    DEMOTE_SCORE_THRESHOLD,
    DEMOTE_STREAK_REQUIRED,
    PROMOTE_SCORE_THRESHOLD,
    PROMOTE_STREAK_REQUIRED,
    STRONG_LESSON_THRESHOLD,
    WEAK_LESSON_THRESHOLD,
)
from app.services.language_listening_challenge.scoring import (
    next_challenge_level,
    prev_challenge_level,
)
from app.services.language_listening_challenge.types import ChallengeLevel, ChallengeState


def evaluate_challenge_adjustment(state: ChallengeState) -> tuple[ChallengeLevel | None, str]:
    """Return a new challenge level (one step) or None if stable."""
    score = state.challenge_score
    current = state.current_level

    if state.promote_streak >= PROMOTE_STREAK_REQUIRED and score >= PROMOTE_SCORE_THRESHOLD:
        nxt = next_challenge_level(current)
        if nxt is not None:
            return nxt, (
                f"promote {current.value}->{nxt.value} "
                f"score={score:.3f} streak={state.promote_streak}"
            )

    if state.demote_streak >= DEMOTE_STREAK_REQUIRED and score <= DEMOTE_SCORE_THRESHOLD:
        prev = prev_challenge_level(current)
        if prev is not None:
            return prev, (
                f"demote {current.value}->{prev.value} "
                f"score={score:.3f} streak={state.demote_streak}"
            )

    return None, "stable"


def apply_challenge_adjustment(state: ChallengeState) -> bool:
    new_level, reason = evaluate_challenge_adjustment(state)
    if new_level is None:
        state.last_adjustment_reason = reason
        return False

    old = state.current_level
    state.current_level = new_level
    state.promote_streak = 0
    state.demote_streak = 0

    if CHALLENGE_LEVEL_ORDER.index(new_level.value) > CHALLENGE_LEVEL_ORDER.index(old.value):
        state.promotion_count += 1
    else:
        state.demotion_count += 1

    entry = {
        "from": old.value,
        "to": new_level.value,
        "score": round(state.challenge_score, 4),
        "reason": reason,
        "lesson_index": state.lesson_index,
    }
    state.adjustment_history.append(entry)
    state.last_adjustment_reason = reason
    return True


def update_streak_counters(state: ChallengeState, lesson_score: float) -> None:
    if lesson_score >= STRONG_LESSON_THRESHOLD:
        state.promote_streak += 1
        state.demote_streak = max(0, state.demote_streak - 1)
    elif lesson_score <= WEAK_LESSON_THRESHOLD:
        state.demote_streak += 1
        state.promote_streak = max(0, state.promote_streak - 1)
    else:
        state.promote_streak = max(0, state.promote_streak - 1)
        state.demote_streak = max(0, state.demote_streak - 1)
