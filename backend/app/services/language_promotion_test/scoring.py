"""Promotion test scoring (Phase 5.4)."""

from __future__ import annotations

from app.services.language_promotion_test.config import DEFAULT_PROMOTION_TEST_CONFIG, PromotionTestConfig
from app.services.language_promotion_test.types import (
    PromotionAssessmentSpec,
    PromotionTestOutcome,
    PromotionTestScoreBreakdown,
    PromotionTestSession,
)


def _clamp100(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def score_to_outcome(overall_score: float, config: PromotionTestConfig = DEFAULT_PROMOTION_TEST_CONFIG) -> PromotionTestOutcome:
    if overall_score >= config.pass_threshold:
        return PromotionTestOutcome.PASS
    if overall_score >= config.borderline_threshold:
        return PromotionTestOutcome.BORDERLINE
    return PromotionTestOutcome.FAIL


def grade_promotion_test_session(
    session: PromotionTestSession,
    answers: dict[str, int],
    *,
    config: PromotionTestConfig = DEFAULT_PROMOTION_TEST_CONFIG,
) -> tuple[PromotionTestScoreBreakdown, int]:
    """Grade submitted answers — returns breakdown and count correct."""
    per_objective: dict[str, list[bool]] = {}
    correct_count = 0

    for assessment in session.assessments:
        submitted = answers.get(assessment.assessment_id)
        if submitted is None:
            submitted = answers.get(assessment.lesson_id, -1)
        is_correct = int(submitted) == assessment.correct_index
        if is_correct:
            correct_count += 1
        per_objective.setdefault(assessment.objective_id, []).append(is_correct)

    total = max(1, len(session.assessments))
    overall = _clamp100(correct_count / total * 100.0)

    objective_scores = {
        oid: _clamp100(sum(results) / len(results) * 100.0)
        for oid, results in per_objective.items()
    }

    covered = len(objective_scores)
    pool_size = len(config.objective_pool)
    coverage_score = _clamp100(covered / max(1, min(pool_size, total)) * 100.0)

    if len(objective_scores) >= 2:
        values = list(objective_scores.values())
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        consistency_score = _clamp100(100.0 - variance)
    else:
        consistency_score = overall * 0.7

    evidence_objectives = [
        oid for oid in objective_scores if oid in {"detail", "inference", "evidence", "announcements"}
    ]
    if evidence_objectives:
        evidence_score = _clamp100(
            sum(objective_scores[oid] for oid in evidence_objectives) / len(evidence_objectives)
        )
    else:
        evidence_score = overall

    exam_confidence = _clamp100(
        0.45 * overall + 0.25 * consistency_score + 0.20 * coverage_score + 0.10 * evidence_score
    )

    breakdown = PromotionTestScoreBreakdown(
        overall_score=overall,
        objective_scores=objective_scores,
        evidence_score=evidence_score,
        consistency_score=consistency_score,
        coverage_score=coverage_score,
        exam_confidence=exam_confidence,
    )
    return breakdown, correct_count


def is_coverage_balanced(session: PromotionTestSession, config: PromotionTestConfig = DEFAULT_PROMOTION_TEST_CONFIG) -> bool:
    counts: dict[str, int] = {}
    for assessment in session.assessments:
        counts[assessment.objective_id] = counts.get(assessment.objective_id, 0) + 1
    if not counts:
        return False
    return max(counts.values()) <= config.max_per_objective
