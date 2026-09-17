"""Promotion test result telemetry (Phase 5.4)."""

from __future__ import annotations

from app.services.language_promotion_test.scoring import score_to_outcome
from app.services.language_promotion_test.types import (
    PromotionTestOutcome,
    PromotionTestResult,
    PromotionTestScoreBreakdown,
    PromotionTestSession,
    PromotionTestTelemetry,
)


def build_strengths_weaknesses(
    breakdown: PromotionTestScoreBreakdown,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    strengths: list[str] = []
    weaknesses: list[str] = []

    for oid, score in sorted(breakdown.objective_scores.items(), key=lambda item: item[1], reverse=True):
        label = oid.replace("_", " ").title()
        if score >= 80:
            strengths.append(f"Strong {label} performance ({score:.0f}%).")
        elif score < 65:
            weaknesses.append(f"Weak {label} performance ({score:.0f}%).")

    if breakdown.consistency_score >= 80:
        strengths.append("Consistent performance across objectives.")
    elif breakdown.consistency_score < 65:
        weaknesses.append("Inconsistent performance across objectives.")

    if breakdown.evidence_score >= 80:
        strengths.append("Solid evidence-focused listening.")
    elif breakdown.evidence_score < 65:
        weaknesses.append("Evidence-focused listening needs improvement.")

    return tuple(strengths[:5]), tuple(weaknesses[:5])


def build_recommendation(outcome: PromotionTestOutcome, weaknesses: tuple[str, ...]) -> str:
    if outcome == PromotionTestOutcome.PASS:
        return "Promotion test passed — official promotion may be applied in a future phase."
    if outcome == PromotionTestOutcome.BORDERLINE:
        return "Borderline result — strengthen weaker objectives and rebuild stable readiness before retaking."
    if weaknesses:
        return f"Focus on {weaknesses[0].split('(')[0].strip().lower()} before attempting again."
    return "Continue targeted listening practice before retaking the promotion test."


def build_promotion_test_result(
    *,
    session: PromotionTestSession,
    breakdown: PromotionTestScoreBreakdown,
    correct_count: int,
) -> PromotionTestResult:
    outcome = score_to_outcome(breakdown.overall_score)
    strengths, weaknesses = build_strengths_weaknesses(breakdown)
    telemetry = PromotionTestTelemetry(
        session_id=session.session_id,
        attempt_number=session.attempt_number,
        official_cefr=session.official_cefr,
        target_cefr=session.target_cefr,
        assessments_correct=correct_count,
        assessments_total=len(session.assessments),
        objective_coverage=session.objective_sequence,
        lesson_ids=session.lesson_ids,
    )
    return PromotionTestResult(
        session_id=session.session_id,
        overall_score=breakdown.overall_score,
        result=outcome,
        objective_scores=dict(breakdown.objective_scores),
        strengths=strengths,
        weaknesses=weaknesses,
        recommendation=build_recommendation(outcome, weaknesses),
        telemetry=telemetry,
        score_breakdown=breakdown,
    )
