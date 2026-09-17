"""Confidence update and decay formulas (Phase 3.2)."""

from __future__ import annotations

from app.services.language_listening_confidence.constants import (
    BASE_ALPHA,
    CONFIDENCE_FLOOR,
    DECAY_RATE_PER_LESSON,
    DECAY_START_LESSONS,
    DIFFICULTY_WEIGHT,
    MAX_ALPHA,
    MAX_DECAY_PER_APPLICATION,
    MAX_GAIN_PER_LESSON,
    MAX_LOSS_PER_LESSON,
    MAX_SINGLE_STEP,
    QUESTION_TYPE_TO_OBJECTIVE,
)
from app.services.language_listening_confidence.types import (
    ConfidenceState,
    LessonConfidenceContext,
    ObjectiveConfidenceRecord,
)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _difficulty_weight(difficulty_band: str) -> float:
    return DIFFICULTY_WEIGHT.get(difficulty_band, 1.0)


def _diversity_bonus(
    ctx: LessonConfidenceContext,
    record: ObjectiveConfidenceRecord,
    *,
    seen_situations: set[str],
    seen_formats: set[str],
) -> float:
    bonus = 1.0
    if ctx.situation and ctx.situation not in seen_situations:
        bonus += 0.12
    if ctx.narrative_format and ctx.narrative_format not in seen_formats:
        bonus += 0.08
    if ctx.speaker_count >= 2:
        bonus += 0.05
    return min(1.3, bonus)


def _consistency_bonus(record: ObjectiveConfidenceRecord) -> float:
    if record.success_streak >= 3:
        return 1.0 + min(0.18, record.success_streak * 0.04)
    return 1.0


def lesson_weight(
    ctx: LessonConfidenceContext,
    record: ObjectiveConfidenceRecord,
    *,
    seen_situations: set[str],
    seen_formats: set[str],
) -> float:
    return (
        _difficulty_weight(ctx.difficulty_band)
        * _diversity_bonus(ctx, record, seen_situations=seen_situations, seen_formats=seen_formats)
        * _consistency_bonus(record)
    )


def apply_confidence_update(
    record: ObjectiveConfidenceRecord,
    *,
    outcome_signal: float,
    weight: float,
) -> float:
    """Weighted EMA update. Returns applied delta (capped for gradual progress)."""
    outcome_signal = _clamp(outcome_signal)
    alpha = min(MAX_ALPHA, BASE_ALPHA * weight)

    if outcome_signal >= 0.5:
        raw_delta = alpha * (outcome_signal - record.confidence)
        delta = min(raw_delta, MAX_GAIN_PER_LESSON)
    else:
        raw_delta = -alpha * (0.55 - outcome_signal) * 1.15
        delta = max(raw_delta, -MAX_LOSS_PER_LESSON)

    delta = _clamp(delta, -MAX_SINGLE_STEP, MAX_SINGLE_STEP)
    previous = record.confidence
    record.confidence = _clamp(record.confidence + delta, CONFIDENCE_FLOOR, 1.0)
    record.trend = round(record.confidence - previous, 4)

    if record.trend > 0:
        record.total_gain += record.trend
        record.success_streak += 1
        record.mistake_streak = 0
    elif record.trend < 0:
        record.total_decay += abs(record.trend)
        record.mistake_streak += 1
        record.success_streak = 0

    record.history.append(record.confidence)
    if len(record.history) > 48:
        record.history = record.history[-48:]
    return record.trend


def apply_decay(
    record: ObjectiveConfidenceRecord,
    *,
    current_lesson_index: int,
) -> float:
    """Very slow confidence decay when an objective is not reviewed."""
    if record.exposure_count == 0:
        return 0.0
    gap = current_lesson_index - record.last_update_index
    if gap <= DECAY_START_LESSONS or record.confidence <= CONFIDENCE_FLOOR + 0.01:
        return 0.0

    overdue = gap - DECAY_START_LESSONS
    decay_amount = min(
        MAX_DECAY_PER_APPLICATION,
        overdue * DECAY_RATE_PER_LESSON * (record.confidence - CONFIDENCE_FLOOR),
    )
    if record.confidence >= 0.85:
        decay_amount *= 0.35
    if decay_amount <= 0:
        return 0.0

    previous = record.confidence
    record.confidence = max(CONFIDENCE_FLOOR, record.confidence - decay_amount)
    record.trend = round(record.confidence - previous, 4)
    record.total_decay += abs(record.trend)
    record.history.append(record.confidence)
    return abs(record.trend)


def apply_decay_to_state(state: ConfidenceState) -> float:
    total = 0.0
    for record in state.objectives.values():
        total += apply_decay(record, current_lesson_index=state.lesson_index)
    return total


def _objectives_from_question_results(
    question_results: list[dict],
    lesson_objectives: tuple[str, ...],
) -> dict[str, float]:
    """Map question outcomes to objective signals (0-1)."""
    signals: dict[str, list[float]] = {oid: [] for oid in lesson_objectives}

    for result in question_results:
        qtype = str(result.get("type") or "detail").lower()
        oid = QUESTION_TYPE_TO_OBJECTIVE.get(qtype, qtype)
        if oid not in signals and oid in lesson_objectives:
            signals[oid] = []
        if oid in signals:
            signals[oid].append(1.0 if result.get("is_correct") else 0.0)

    out: dict[str, float] = {}
    for oid, values in signals.items():
        if values:
            out[oid] = sum(values) / len(values)
    return out


def update_confidence_from_lesson(
    state: ConfidenceState,
    ctx: LessonConfidenceContext,
    question_results: list[dict],
    *,
    seen_situations: set[str] | None = None,
    seen_formats: set[str] | None = None,
) -> ConfidenceState:
    """Update every objective involved in a completed lesson."""
    seen_situations = seen_situations or set()
    seen_formats = seen_formats or set()
    state.lesson_index = max(state.lesson_index, ctx.lesson_index)

    objective_signals = _objectives_from_question_results(question_results, ctx.lesson_objectives)
    overall_correct = (
        sum(1 for r in question_results if r.get("is_correct")) / max(1, len(question_results))
        if question_results
        else 0.5
    )

    involved = set(ctx.lesson_objectives)
    for skill in ctx.skill_focus:
        if skill in state.objectives:
            involved.add(skill)

    for oid in involved:
        record = state.objectives.get(oid)
        if record is None:
            continue
        signal = objective_signals.get(oid, overall_correct)
        weight = lesson_weight(
            ctx,
            record,
            seen_situations=seen_situations,
            seen_formats=seen_formats,
        )
        apply_confidence_update(record, outcome_signal=signal, weight=weight)
        record.last_update_index = ctx.lesson_index
        record.exposure_count += 1

    return state
