"""Confidence-aware objective selection (Phase 3.2)."""

from __future__ import annotations

from app.services.language_listening_confidence.constants import (
    MASTERY_THRESHOLD,
    REVIEW_CONFIDENCE_MIN,
    REVIEW_INTERVAL,
)
from app.services.language_listening_confidence.types import ConfidenceState
from app.services.language_listening_curriculum.intent import LessonIntent


def _review_due(state: ConfidenceState, generation_index: int) -> list[str]:
    due: list[tuple[int, str]] = []
    for oid, rec in state.objectives.items():
        if rec.is_mastered and generation_index - rec.last_update_index >= REVIEW_INTERVAL:
            due.append((rec.last_update_index, oid))
        elif (
            rec.confidence >= REVIEW_CONFIDENCE_MIN
            and rec.coverage_score >= 0.55
            and generation_index - rec.last_update_index >= REVIEW_INTERVAL
        ):
            due.append((rec.last_update_index, oid))
    due.sort(key=lambda x: x[0])
    return [oid for _, oid in due]


def has_review_due_confidence(state: ConfidenceState, generation_index: int) -> bool:
    return bool(_review_due(state, generation_index))


def objectives_for_lesson_confidence(
    state: ConfidenceState,
    *,
    generation_index: int,
    intent: LessonIntent,
    max_count: int = 2,
) -> tuple[tuple[str, ...], tuple[str, ...], bool]:
    """Select objectives by confidence — lower confidence gets higher priority."""
    review_due_list = _review_due(state, generation_index)
    reviews = tuple(review_due_list[:1])

    ranked = sorted(state.objectives.items(), key=lambda x: (x[1].mastery_score, x[0]))
    low_conf = [oid for oid, rec in ranked if not rec.is_mastered]
    needs_evidence = [
        oid
        for oid, rec in sorted(state.objectives.items(), key=lambda x: (x[1].coverage_score, x[0]))
        if rec.confidence >= 0.70 and rec.coverage_score < 0.55
    ]
    unseen = [oid for oid, rec in ranked if rec.exposure_count == 0]

    def _rotated(ids: list[str], count: int) -> list[str]:
        if not ids:
            return []
        start = generation_index % len(ids)
        return (ids[start:] + ids[:start])[:count]

    focus: list[str] = []
    if intent == LessonIntent.review and reviews:
        focus.append(reviews[0])
    elif intent == LessonIntent.exploration and unseen:
        focus.extend(_rotated(unseen, max_count))
    elif intent == LessonIntent.balanced_coverage and needs_evidence:
        focus.extend(_rotated(needs_evidence, max_count))
    elif intent == LessonIntent.weak_recovery:
        focus.extend(_rotated(low_conf[: max(len(low_conf), max_count)], max_count))
    else:
        focus.extend(_rotated(low_conf, max_count))

    if not focus and low_conf:
        focus = [low_conf[0]]
    if not focus and state.objectives:
        focus = [next(iter(state.objectives))]

    if reviews and reviews[0] not in focus and intent != LessonIntent.exploration:
        focus = focus[: max(1, max_count - 1)] + [reviews[0]]

    low_conf = [oid for oid, rec in ranked if rec.confidence < 0.55]
    if intent == LessonIntent.weak_recovery and low_conf and low_conf[0] not in focus:
        focus = [low_conf[0]] + [f for f in focus if f != low_conf[0]]
        focus = focus[:max_count]

    return tuple(focus[:max_count]), reviews, bool(review_due_list)


def confidence_review_priority_score(
    objectives: tuple[str, ...],
    state: ConfidenceState,
    generation_index: int,
) -> float:
    score = 0.0
    for oid in objectives:
        rec = state.objectives.get(oid)
        if not rec:
            continue
        if rec.confidence >= MASTERY_THRESHOLD and generation_index - rec.last_update_index >= REVIEW_INTERVAL:
            score += 1.0
        elif rec.confidence >= 0.70 and rec.coverage_score < 0.55:
            score += 0.9
        elif rec.confidence < 0.45:
            score += 0.85
        elif rec.confidence < 0.65:
            score += 0.65
        elif rec.confidence < MASTERY_THRESHOLD:
            score += 0.45
    return min(1.0, score / 2.0)


def confidence_priority_weight(state: ConfidenceState, objectives: tuple[str, ...]) -> float:
    """Higher weight when lesson targets low-confidence objectives."""
    if not objectives:
        return 0.5
    deficits = []
    for oid in objectives:
        rec = state.objectives.get(oid)
        if rec:
            if rec.confidence >= 0.70 and rec.coverage_score < 0.60:
                deficits.append(1.0 - rec.coverage_score)
            else:
                deficits.append(1.0 - rec.confidence)
    if not deficits:
        return 0.5
    avg_deficit = sum(deficits) / len(deficits)
    return min(1.0, 0.35 + avg_deficit * 0.65)
