"""Listening Official Promotion Engine (Phase 5.5).

Consumes Promotion Test PASS results and applies Official CEFR promotion.
Never modifies Reading, Speaking, or Writing official levels.

POLICY: This engine is the ONLY runtime writer of official_listening_cefr.
Placement initializes levels; lesson submit and promotion test never promote.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.progression import LanguageProgression
from app.services.language_learning_stage.types import ListeningLearningStage, stage_label
from app.services.language_listening_progression.locking import lock_listening_progression_row
from app.services.language_official_promotion.events import record_official_listening_promotion_event
from app.services.language_official_promotion.storage import (
    append_promotion_record,
    find_promotion_test_attempt,
    get_latest_promotion_test_attempt,
    is_session_already_promoted,
    promote_listening_official_cefr,
    resolve_recommended_next_listening_lesson,
)
from app.services.language_official_promotion.telemetry import (
    build_denied_result,
    build_journey_reset_snapshot,
    build_official_promotion_telemetry,
    build_post_promotion_summary,
)
from app.services.language_official_promotion.types import PromotionAppliedResult
from app.services.language_progression_service import get_official_cefr
from app.services.language_promotion_test.session import pop_session
from app.services.language_promotion_test.types import PromotionTestOutcome


async def apply_listening_official_promotion(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    session_id: str | None = None,
    locked_row: LanguageProgression | None = None,
) -> PromotionAppliedResult:
    """Apply official listening promotion when the latest (or specified) test is PASS.

    Idempotent: re-applying for the same session_id returns success without duplicate promotion.
    Acquires a row lock when locked_row is not supplied.
    """
    row = locked_row
    if row is None:
        row = await lock_listening_progression_row(
            db, student_id=student_id, language_id=language_id
        )
    if row is None:
        official = await get_official_cefr(
            db, student_id=student_id, language_id=language_id, skill=LanguageSkill.listening
        )
        return build_denied_result(
            attempt=None,
            old_cefr=official.level.value,
            denial_reason="No progression row found.",
        )

    payload = dict(row.promotion_readiness_json or {})
    old_cefr = row.official_listening_cefr.value

    attempt = (
        find_promotion_test_attempt(payload, session_id=session_id)
        if session_id
        else get_latest_promotion_test_attempt(payload)
    )
    if attempt is None:
        return build_denied_result(
            attempt=None,
            old_cefr=old_cefr,
            denial_reason="No promotion test attempt found.",
        )

    if attempt.result != PromotionTestOutcome.PASS.value:
        return build_denied_result(
            attempt=attempt,
            old_cefr=old_cefr,
            denial_reason=f"Promotion requires PASS (latest result: {attempt.result}).",
        )

    if is_session_already_promoted(payload, attempt.session_id):
        existing_events = (payload.get("listening_official_promotions") or {}).get("events") or []
        existing = next(
            (e for e in reversed(existing_events) if isinstance(e, dict) and e.get("session_id") == attempt.session_id),
            None,
        )
        new_cefr = str(existing.get("new_cefr", attempt.target_cefr)) if existing else attempt.target_cefr
        journey = build_journey_reset_snapshot(
            preserved_exam_history=True,
            preserved_stability_history=True,
            preserved_promotion_history=True,
            session_closed=True,
        )
        telemetry = build_official_promotion_telemetry(
            attempt=attempt,
            previous_overall_cefr=row.official_overall_cefr.value,
            new_overall_cefr=row.official_overall_cefr.value,
            overall_updated=False,
            promoted_at=str(existing.get("promoted_at", "")) if existing else "",
        )
        stage_label_text = stage_label(
            official_cefr=new_cefr,
            stage=ListeningLearningStage(int(row.learning_stage_listening or 1)),
        )
        lesson = await resolve_recommended_next_listening_lesson(
            db, student_id=student_id, language_id=language_id, level=new_cefr
        )
        return PromotionAppliedResult(
            old_cefr=attempt.official_cefr.upper(),
            new_cefr=new_cefr.upper(),
            promotion_success=True,
            new_learning_stage=int(row.learning_stage_listening or 1),
            journey_reset=journey,
            event_id=int(existing.get("event_id")) if existing and existing.get("event_id") else None,
            telemetry=telemetry,
            summary=build_post_promotion_summary(
                old_cefr=attempt.official_cefr,
                new_cefr=new_cefr,
                new_stage_label=stage_label_text,
                recommended_lesson=lesson,
            ),
            denial_reason=None,
        )

    try:
        new_level = LanguageLevel(attempt.target_cefr.upper())
    except ValueError:
        return build_denied_result(
            attempt=attempt,
            old_cefr=old_cefr,
            denial_reason=f"Invalid target CEFR: {attempt.target_cefr}.",
        )

    previous_overall, new_overall, overall_updated = await promote_listening_official_cefr(
        row, new_listening=new_level
    )
    from app.services.language_progression_service import sync_analytics_listening_level

    await sync_analytics_listening_level(
        db,
        student_id=student_id,
        language_id=language_id,
        listening_level=new_level,
    )
    promoted_at = datetime.now(timezone.utc).isoformat()

    preserved_tests = bool((payload.get("listening_promotion_tests") or {}).get("attempts"))
    preserved_stability = bool((payload.get("stability") or {}).get("history"))
    preserved_promotions = bool((payload.get("listening_official_promotions") or {}).get("events"))

    journey = build_journey_reset_snapshot(
        preserved_exam_history=preserved_tests,
        preserved_stability_history=preserved_stability,
        preserved_promotion_history=preserved_promotions,
        session_closed=True,
    )
    telemetry = build_official_promotion_telemetry(
        attempt=attempt,
        previous_overall_cefr=previous_overall,
        new_overall_cefr=new_overall,
        overall_updated=overall_updated,
        promoted_at=promoted_at,
    )

    event_id = await record_official_listening_promotion_event(
        db,
        student_id=student_id,
        language_id=language_id,
        payload_json={
            "session_id": attempt.session_id,
            "attempt_number": attempt.attempt_number,
            "old_cefr": attempt.official_cefr,
            "new_cefr": attempt.target_cefr,
            "promotion_test_score": attempt.overall_score,
            "promotion_reason": "Promotion test PASS",
            "promoted_at": promoted_at,
            "overall_cefr_updated": overall_updated,
            "previous_overall_cefr": previous_overall,
            "new_overall_cefr": new_overall,
            "telemetry": {
                "promotion_test_session_id": attempt.session_id,
                "promotion_test_attempt_number": attempt.attempt_number,
            },
        },
    )

    await append_promotion_record(
        db,
        student_id=student_id,
        language_id=language_id,
        event_id=event_id,
        attempt=attempt,
        telemetry_snapshot={
            "old_cefr": attempt.official_cefr,
            "new_cefr": attempt.target_cefr,
            "promotion_test_score": attempt.overall_score,
            "attempt_number": attempt.attempt_number,
            "overall_cefr_updated": overall_updated,
        },
        journey_reset={
            "learning_stage": journey.learning_stage,
            "promotion_readiness_score": journey.promotion_readiness_score,
            "promotion_confidence": journey.promotion_confidence,
            "transition_gate_reset": journey.transition_gate_reset,
        },
        locked_row=row,
    )
    await pop_session(
        db,
        attempt.session_id,
        student_id=student_id,
        language_id=language_id,
        locked_row=row,
    )
    await db.flush()

    new_stage_label = stage_label(
        official_cefr=attempt.target_cefr,
        stage=ListeningLearningStage.beginner,
    )
    lesson = await resolve_recommended_next_listening_lesson(
        db, student_id=student_id, language_id=language_id, level=attempt.target_cefr
    )
    summary = build_post_promotion_summary(
        old_cefr=attempt.official_cefr,
        new_cefr=attempt.target_cefr,
        new_stage_label=new_stage_label,
        recommended_lesson=lesson,
    )

    return PromotionAppliedResult(
        old_cefr=attempt.official_cefr.upper(),
        new_cefr=attempt.target_cefr.upper(),
        promotion_success=True,
        new_learning_stage=int(ListeningLearningStage.beginner),
        journey_reset=journey,
        event_id=event_id,
        telemetry=telemetry,
        summary=summary,
        denial_reason=None,
    )
