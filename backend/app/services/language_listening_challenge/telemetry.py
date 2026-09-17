"""Challenge telemetry (Phase 3.3)."""

from __future__ import annotations

from app.services.language_listening_challenge.types import ChallengeState, ChallengeTelemetry


def compute_challenge_telemetry(state: ChallengeState) -> ChallengeTelemetry:
    history_labels = [
        f"L{rec.lesson_index}:{rec.lesson_score:.2f}" for rec in state.history[-15:]
    ]
    avg_lesson = (
        sum(rec.lesson_score for rec in state.history) / len(state.history)
        if state.history
        else 0.5
    )
    return ChallengeTelemetry(
        level=state.level,
        current_challenge=state.current_level.value,
        challenge_score=round(state.challenge_score, 4),
        promotion_count=state.promotion_count,
        demotion_count=state.demotion_count,
        promote_streak=state.promote_streak,
        demote_streak=state.demote_streak,
        lesson_index=state.lesson_index,
        average_lesson_score=round(avg_lesson, 4),
        challenge_history=history_labels,
        adjustment_history=list(state.adjustment_history[-16:]),
        last_adjustment_reason=state.last_adjustment_reason,
    )
