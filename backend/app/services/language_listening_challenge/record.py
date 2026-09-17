"""Record lesson outcomes and refresh challenge state (Phase 3.3)."""

from __future__ import annotations

from app.services.language_listening_challenge.adjustment import (
    apply_challenge_adjustment,
    update_streak_counters,
)
from app.services.language_listening_challenge.constants import HISTORY_WINDOW
from app.services.language_listening_challenge.scoring import (
    compute_challenge_score,
    compute_lesson_performance_score,
)
from app.services.language_listening_challenge.types import ChallengeLessonRecord, ChallengeState
from app.services.language_listening_confidence.types import ConfidenceState, LessonConfidenceContext


def _avg_confidence_trend(
    confidence_state: ConfidenceState,
    objectives: tuple[str, ...],
) -> float:
    if not objectives:
        trends = [rec.trend for rec in confidence_state.objectives.values()]
    else:
        trends = [
            confidence_state.objectives[oid].trend
            for oid in objectives
            if oid in confidence_state.objectives
        ]
    if not trends:
        return 0.0
    return sum(trends) / len(trends)


def _evidence_growth(
    confidence_state: ConfidenceState,
    objectives: tuple[str, ...],
    *,
    before_coverages: dict[str, float] | None = None,
) -> float:
    if not before_coverages:
        return 0.05
    delta = 0.0
    count = 0
    for oid in objectives:
        rec = confidence_state.objectives.get(oid)
        if rec is None:
            continue
        before = before_coverages.get(oid, rec.coverage_score)
        delta += max(0.0, rec.coverage_score - before)
        count += 1
    return delta / max(1, count)


def record_challenge_from_lesson(
    state: ChallengeState,
    confidence_state: ConfidenceState,
    lesson_ctx: LessonConfidenceContext,
    *,
    score_percent: float,
    passed: bool,
    question_results: list[dict] | None = None,
    was_review: bool = False,
    time_spent_sec: float | None = None,
    hint_count: int = 0,
    retry_count: int = 1,
    before_coverages: dict[str, float] | None = None,
) -> ChallengeLessonRecord:
    accuracy = max(0.0, min(1.0, score_percent / 100.0))
    objectives = lesson_ctx.lesson_objectives + lesson_ctx.skill_focus
    trend = _avg_confidence_trend(confidence_state, objectives)
    evidence_growth = _evidence_growth(confidence_state, objectives, before_coverages=before_coverages)

    success_streak = max(
        (confidence_state.objectives[oid].success_streak for oid in objectives if oid in confidence_state.objectives),
        default=0,
    )
    failure_streak = max(
        (confidence_state.objectives[oid].mistake_streak for oid in objectives if oid in confidence_state.objectives),
        default=0,
    )

    review_perf = accuracy if was_review else accuracy
    lesson_score = compute_lesson_performance_score(
        accuracy=accuracy,
        passed=passed,
        confidence_trend=trend,
        evidence_growth=evidence_growth,
        review_performance=review_perf,
        was_review=was_review,
        success_streak=success_streak,
        failure_streak=failure_streak,
        time_spent_sec=time_spent_sec,
        hint_count=hint_count,
        retry_count=retry_count,
    )

    state.lesson_index = max(state.lesson_index, lesson_ctx.lesson_index)
    record = ChallengeLessonRecord(
        lesson_index=lesson_ctx.lesson_index,
        accuracy=accuracy,
        passed=passed,
        confidence_trend=trend,
        evidence_growth=evidence_growth,
        review_performance=review_perf,
        was_review=was_review,
        success_streak=success_streak,
        failure_streak=failure_streak,
        time_spent_sec=time_spent_sec,
        hint_count=hint_count,
        retry_count=retry_count,
        lesson_score=lesson_score,
    )
    state.history.append(record)
    state.history = state.history[-HISTORY_WINDOW:]

    update_streak_counters(state, lesson_score)
    state.challenge_score = compute_challenge_score(state, confidence_state)
    apply_challenge_adjustment(state)
    return record
