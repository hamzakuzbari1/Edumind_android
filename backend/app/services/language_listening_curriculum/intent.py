"""Balanced lesson intent selection (Phase 2.3.1)."""

from __future__ import annotations

from collections import Counter
from enum import StrEnum


class LessonIntent(StrEnum):
    weak_recovery = "weak_recovery"
    review = "review"
    balanced_coverage = "balanced_coverage"
    exploration = "exploration"


# Adaptive target bands (centres used for deficit calculation)
INTENT_TARGETS: dict[LessonIntent, float] = {
    LessonIntent.weak_recovery: 0.30,
    LessonIntent.review: 0.175,
    LessonIntent.balanced_coverage: 0.40,
    LessonIntent.exploration: 0.125,
}

INTENT_BANDS: dict[LessonIntent, tuple[float, float]] = {
    LessonIntent.weak_recovery: (0.25, 0.35),
    LessonIntent.review: (0.15, 0.20),
    LessonIntent.balanced_coverage: (0.35, 0.45),
    LessonIntent.exploration: (0.10, 0.20),
}

INTENT_WINDOW = 40


def pick_lesson_intent(
    recent_intents: list[str],
    *,
    review_due: bool,
    has_weak_skills: bool,
    recent_primary_weak_share: float = 0.0,
) -> LessonIntent:
    """Choose lesson intent to keep educational mix near target bands."""
    window = recent_intents[-INTENT_WINDOW:]
    total = len(window) or 1
    counts = Counter(window)
    shares = {intent.value: counts.get(intent.value, 0) / total for intent in LessonIntent}

    deficits: dict[LessonIntent, float] = {}
    for intent, target in INTENT_TARGETS.items():
        deficits[intent] = target - shares.get(intent.value, 0.0)

    # Soft caps — never let one intent dominate
    low, high = INTENT_BANDS[LessonIntent.weak_recovery]
    if shares.get(LessonIntent.weak_recovery.value, 0) >= high:
        deficits[LessonIntent.weak_recovery] -= 1.0
    elif shares.get(LessonIntent.weak_recovery.value, 0) >= low + 0.05:
        deficits[LessonIntent.weak_recovery] -= 0.35

    if recent_primary_weak_share >= high:
        deficits[LessonIntent.weak_recovery] -= 0.9
    elif recent_primary_weak_share >= low + 0.02:
        deficits[LessonIntent.weak_recovery] -= 0.45

    low, high = INTENT_BANDS[LessonIntent.review]
    if shares.get(LessonIntent.review.value, 0) >= high:
        deficits[LessonIntent.review] -= 0.8

    low, high = INTENT_BANDS[LessonIntent.balanced_coverage]
    if shares.get(LessonIntent.balanced_coverage.value, 0) < low:
        deficits[LessonIntent.balanced_coverage] += 0.25

    # Nudge when signals exist but intent is underused
    if review_due and shares.get(LessonIntent.review.value, 0) < INTENT_TARGETS[LessonIntent.review]:
        deficits[LessonIntent.review] += 0.2
    if has_weak_skills and shares.get(LessonIntent.weak_recovery.value, 0) < INTENT_TARGETS[LessonIntent.weak_recovery]:
        deficits[LessonIntent.weak_recovery] += 0.15

    if not has_weak_skills:
        deficits[LessonIntent.weak_recovery] -= 0.5

    return max(deficits, key=lambda k: deficits[k])


def intent_distribution(recent_intents: list[str]) -> dict[str, float]:
    window = recent_intents[-INTENT_WINDOW:]
    total = len(window) or 1
    counts = Counter(window)
    return {intent.value: round(counts.get(intent.value, 0) / total, 3) for intent in LessonIntent}
