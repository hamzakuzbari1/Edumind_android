"""Post-promotion telemetry and summary (Phase 5.5)."""

from __future__ import annotations

from app.services.language_learning_stage.types import STAGE_DISPLAY_NAMES, ListeningLearningStage, stage_label
from app.services.language_official_promotion.types import (
    JourneyResetSnapshot,
    OfficialPromotionTelemetry,
    PromotionAppliedResult,
    PromotionTestAttemptRef,
)


def build_journey_reset_snapshot(
    *,
    preserved_exam_history: bool,
    preserved_stability_history: bool,
    preserved_promotion_history: bool,
    session_closed: bool,
) -> JourneyResetSnapshot:
    stage = ListeningLearningStage.beginner
    return JourneyResetSnapshot(
        learning_stage=int(stage),
        learning_stage_name=STAGE_DISPLAY_NAMES[stage],
        promotion_readiness_score=0,
        promotion_confidence=0,
        transition_gate_reset=True,
        promotion_test_session_closed=session_closed,
        preserved_exam_history=preserved_exam_history,
        preserved_stability_history=preserved_stability_history,
        preserved_promotion_history=preserved_promotion_history,
    )


def build_official_promotion_telemetry(
    *,
    attempt: PromotionTestAttemptRef,
    previous_overall_cefr: str,
    new_overall_cefr: str,
    overall_updated: bool,
    promoted_at: str,
) -> OfficialPromotionTelemetry:
    return OfficialPromotionTelemetry(
        old_cefr=attempt.official_cefr.upper(),
        new_cefr=attempt.target_cefr.upper(),
        promotion_test_session_id=attempt.session_id,
        promotion_test_score=attempt.overall_score,
        promotion_test_attempt_number=attempt.attempt_number,
        promotion_reason="Promotion test PASS",
        promoted_at=promoted_at,
        overall_cefr_updated=overall_updated,
        previous_overall_cefr=previous_overall_cefr,
        new_overall_cefr=new_overall_cefr,
    )


def build_post_promotion_summary(
    *,
    old_cefr: str,
    new_cefr: str,
    new_stage_label: str,
    recommended_lesson: str | None,
) -> str:
    lesson_line = recommended_lesson or f"Listening lesson at {new_cefr}"
    return (
        f"Congratulations.\n\n"
        f"You officially advanced from {old_cefr.upper()} to {new_cefr.upper()}.\n\n"
        f"Your new journey begins as {new_stage_label}.\n\n"
        f"Your previous learning history has been preserved.\n\n"
        f"Your Promotion Readiness has been reset for the next promotion cycle.\n\n"
        f"Recommended next lesson:\n{lesson_line}"
    )


def build_denied_result(
    *,
    attempt: PromotionTestAttemptRef | None,
    old_cefr: str,
    denial_reason: str,
) -> PromotionAppliedResult:
    journey = build_journey_reset_snapshot(
        preserved_exam_history=True,
        preserved_stability_history=True,
        preserved_promotion_history=True,
        session_closed=False,
    )
    telemetry = OfficialPromotionTelemetry(
        old_cefr=old_cefr.upper(),
        new_cefr=old_cefr.upper(),
        promotion_test_session_id=attempt.session_id if attempt else "",
        promotion_test_score=attempt.overall_score if attempt else 0.0,
        promotion_test_attempt_number=attempt.attempt_number if attempt else 0,
        promotion_reason=denial_reason,
        promoted_at="",
        overall_cefr_updated=False,
        previous_overall_cefr=old_cefr.upper(),
        new_overall_cefr=old_cefr.upper(),
    )
    return PromotionAppliedResult(
        old_cefr=old_cefr.upper(),
        new_cefr=old_cefr.upper(),
        promotion_success=False,
        new_learning_stage=int(ListeningLearningStage.beginner),
        journey_reset=journey,
        event_id=None,
        telemetry=telemetry,
        summary="",
        denial_reason=denial_reason,
    )
