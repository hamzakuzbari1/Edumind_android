"""Adaptive coach tone architecture (W2.1 frozen) — communication only, never pedagogical facts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.services.language_writing.enums import WritingCoachPersonality


class AdaptiveToneTrigger(StrEnum):
    """Signals that adjust communication style — personality remains fixed."""

    student_frustration = "student_frustration"
    recent_improvement = "recent_improvement"
    repeated_failures = "repeated_failures"
    long_inactivity = "long_inactivity"
    high_confidence = "high_confidence"


class AdaptiveToneAdjustment(StrEnum):
    """Permitted tone adjustments — educational content unchanged."""

    more_patience = "more_patience"
    more_encouragement = "more_encouragement"
    shorter_sentences = "shorter_sentences"
    slower_pace = "slower_pace"
    celebrate_progress = "celebrate_progress"
    re_engagement_welcome = "re_engagement_welcome"
    forward_challenge = "forward_challenge"
    reduce_pressure = "reduce_pressure"


# Frozen mapping — future runtime applies adjustments as rendering directives only.
TONE_ADJUSTMENT_MAP: dict[AdaptiveToneTrigger, tuple[AdaptiveToneAdjustment, ...]] = {
    AdaptiveToneTrigger.student_frustration: (
        AdaptiveToneAdjustment.more_patience,
        AdaptiveToneAdjustment.shorter_sentences,
        AdaptiveToneAdjustment.reduce_pressure,
    ),
    AdaptiveToneTrigger.recent_improvement: (
        AdaptiveToneAdjustment.celebrate_progress,
        AdaptiveToneAdjustment.more_encouragement,
    ),
    AdaptiveToneTrigger.repeated_failures: (
        AdaptiveToneAdjustment.more_patience,
        AdaptiveToneAdjustment.slower_pace,
        AdaptiveToneAdjustment.shorter_sentences,
    ),
    AdaptiveToneTrigger.long_inactivity: (
        AdaptiveToneAdjustment.re_engagement_welcome,
        AdaptiveToneAdjustment.reduce_pressure,
    ),
    AdaptiveToneTrigger.high_confidence: (
        AdaptiveToneAdjustment.forward_challenge,
    ),
}


@dataclass(frozen=True, slots=True)
class AdaptiveToneContext:
    """Input signals for tone adaptation — derived from memory + session, not evaluator."""

    personality: WritingCoachPersonality
    active_triggers: tuple[AdaptiveToneTrigger, ...]
    adjustments: tuple[AdaptiveToneAdjustment, ...]
    architecture_version: str = "2.1.0"

    @staticmethod
    def resolve(
        *,
        personality: WritingCoachPersonality,
        triggers: tuple[AdaptiveToneTrigger, ...],
    ) -> AdaptiveToneContext:
        seen: list[AdaptiveToneAdjustment] = []
        for trigger in triggers:
            for adj in TONE_ADJUSTMENT_MAP.get(trigger, ()):
                if adj not in seen:
                    seen.append(adj)
        return AdaptiveToneContext(
            personality=personality,
            active_triggers=triggers,
            adjustments=tuple(seen),
        )


# Invariant (frozen): adaptive tone MUST NOT change:
# - priority_issue from evaluator
# - ready_to_complete_signal
# - learning_outcomes
# - success_criteria
# - revision_mission substance (only phrasing)

ADAPTIVE_TONE_INVARIANTS: tuple[str, ...] = (
    "Personality enum value is fixed for the session goal profile.",
    "Evaluator priority issue and ready_to_complete signal are immutable.",
    "Learning outcomes and success criteria text are unchanged.",
    "Only sentence length, warmth, pacing, and encouragement density may shift.",
)
