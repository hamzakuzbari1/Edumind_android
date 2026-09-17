"""Speaking Official Promotion Engine (S20).

Sole runtime writer of ``official_speaking_cefr`` after a PASS SPA assessment.
Consumes S19 results — never re-scores SPA, never runs readiness/S7.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.progression import LanguageProgression
from app.services.language_level_utils import bottleneck_level
from app.services.language_progression_service import get_official_cefr
from app.services.language_speaking.enums import SpeakingLearningStage
from app.services.language_speaking_progression.locking import lock_speaking_progression_row
from app.services.language_speaking_official_promotion.events import (
    record_official_speaking_promotion_event,
)
from app.services.language_speaking_official_promotion.storage import (
    append_speaking_promotion_record,
    assessment_is_consumed,
    find_promotion_pass_assessment,
    is_assessment_already_promoted,
    is_attempt_already_promoted,
    last_promotion_for_attempt,
    mark_assessment_consumed_in_payload,
    reset_speaking_promotion_readiness_projection,
)
from app.services.language_speaking_official_promotion.types import SpeakingOfficialPromotionResult
from app.services.language_speaking_promotion_test.execution_types import SpaAssessmentOutcome
from app.services.language_speaking_promotion_test.unlock import resolve_next_speaking_cefr_local


def _denied(
    *,
    old_cefr: str,
    reason: str,
    assessment_id: str = "",
    attempt_id: str = "",
) -> SpeakingOfficialPromotionResult:
    return SpeakingOfficialPromotionResult(
        success=False,
        old_cefr=old_cefr,
        new_cefr=old_cefr,
        reason=reason,
        assessment_id=assessment_id,
        attempt_id=attempt_id,
    )


async def apply_speaking_official_promotion(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    assessment_id: str | None = None,
    attempt_id: str | None = None,
    locked_row: LanguageProgression | None = None,
) -> SpeakingOfficialPromotionResult:
    """Apply official speaking CEFR promotion from a validated SPA PASS.

    Idempotent: re-applying the same attempt returns success without a second CEFR write.
    """
    row = locked_row
    if row is None:
        row = await lock_speaking_progression_row(
            db, student_id=student_id, language_id=language_id
        )
    if row is None:
        official = await get_official_cefr(
            db, student_id=student_id, language_id=language_id, skill=LanguageSkill.speaking
        )
        return _denied(old_cefr=official.level.value, reason="No progression row found.")

    payload = dict(row.promotion_readiness_json or {})
    old_cefr = row.official_speaking_cefr.value

    assessment = find_promotion_pass_assessment(
        payload,
        assessment_id=assessment_id,
        attempt_id=attempt_id,
        include_consumed=True,
    )
    if assessment is None:
        return _denied(old_cefr=old_cefr, reason="No speaking promotion assessment found.")

    aid = assessment.assessment_id
    result = assessment.result
    if result is None:
        return _denied(
            old_cefr=old_cefr,
            reason="Assessment has no result.",
            assessment_id=aid,
        )

    attempt_key = attempt_id or result.attempt_id
    if not attempt_key:
        return _denied(
            old_cefr=old_cefr,
            reason="Assessment attempt missing.",
            assessment_id=aid,
        )

    # Idempotent replay
    if is_attempt_already_promoted(payload, attempt_key) or is_assessment_already_promoted(
        payload, aid
    ):
        existing = last_promotion_for_attempt(payload, attempt_key)
        new_cefr = (
            str(existing.get("new_cefr") or assessment.blueprint.target_cefr).upper()
            if existing
            else assessment.blueprint.target_cefr.upper()
        )
        return SpeakingOfficialPromotionResult(
            success=True,
            old_cefr=str(existing.get("old_cefr") or old_cefr).upper() if existing else old_cefr,
            new_cefr=new_cefr,
            reason="Already promoted.",
            assessment_id=aid,
            attempt_id=attempt_key,
            promoted_at=str(existing.get("promoted_at") or "") if existing else "",
            already_promoted=True,
            ready_for_new_journey=True,
        )

    if result.outcome != SpaAssessmentOutcome.PASS:
        return _denied(
            old_cefr=old_cefr,
            reason=f"Promotion requires PASS (latest result: {result.outcome.value}).",
            assessment_id=aid,
            attempt_id=attempt_key,
        )

    if not result.ready_for_official_promotion:
        # Consumed assessments clear this flag.
        if assessment_is_consumed(payload, aid):
            return _denied(
                old_cefr=old_cefr,
                reason="Assessment already consumed by an official promotion.",
                assessment_id=aid,
                attempt_id=attempt_key,
            )
        return _denied(
            old_cefr=old_cefr,
            reason="Assessment is not ready for official promotion.",
            assessment_id=aid,
            attempt_id=attempt_key,
        )

    if assessment_is_consumed(payload, aid):
        return _denied(
            old_cefr=old_cefr,
            reason="Assessment already consumed by an official promotion.",
            assessment_id=aid,
            attempt_id=attempt_key,
        )

    blueprint = assessment.blueprint
    if not blueprint.frozen:
        return _denied(
            old_cefr=old_cefr,
            reason="Assessment blueprint is not frozen.",
            assessment_id=aid,
            attempt_id=attempt_key,
        )
    if not blueprint.blueprint_fingerprint or not blueprint.specification_fingerprint:
        return _denied(
            old_cefr=old_cefr,
            reason="Assessment integrity fingerprints missing.",
            assessment_id=aid,
            attempt_id=attempt_key,
        )

    source = (blueprint.source_cefr or "").upper()
    target = (blueprint.target_cefr or "").upper()
    if old_cefr.upper() != source:
        return _denied(
            old_cefr=old_cefr,
            reason="Official CEFR no longer matches assessment source level (stale).",
            assessment_id=aid,
            attempt_id=attempt_key,
        )

    try:
        expected_target = resolve_next_speaking_cefr_local(source)
    except ValueError as exc:
        return _denied(
            old_cefr=old_cefr,
            reason=f"Invalid promotion target path: {exc}",
            assessment_id=aid,
            attempt_id=attempt_key,
        )
    if target != expected_target.upper():
        return _denied(
            old_cefr=old_cefr,
            reason="Assessment target CEFR is not the next consecutive level.",
            assessment_id=aid,
            attempt_id=attempt_key,
        )
    try:
        new_level = LanguageLevel(target)
    except ValueError:
        return _denied(
            old_cefr=old_cefr,
            reason="Invalid target CEFR.",
            assessment_id=aid,
            attempt_id=attempt_key,
        )

    # --- sole official_speaking_cefr write ---
    row.official_speaking_cefr = new_level
    row.official_overall_cefr = (
        bottleneck_level(
            {
                "reading": row.official_reading_cefr,
                "listening": row.official_listening_cefr,
                "writing": row.official_writing_cefr,
                "speaking": new_level,
            }
        )
        or new_level
    )
    row.learning_stage_speaking = int(SpeakingLearningStage.foundation)
    row.promotion_readiness_score = 0
    now = datetime.now(timezone.utc)
    row.last_promotion_at = now
    row.version = int(row.version or 0) + 1
    promoted_at = now.isoformat()

    updated = append_speaking_promotion_record(
        payload,
        assessment_id=aid,
        attempt_id=attempt_key,
        old_cefr=old_cefr,
        new_cefr=target,
        promoted_at=promoted_at,
    )
    updated = mark_assessment_consumed_in_payload(
        updated,
        assessment_id=aid,
        attempt_id=attempt_key,
        consumed_at=promoted_at,
    )
    updated = reset_speaking_promotion_readiness_projection(
        updated, new_official_cefr=target
    )
    row.promotion_readiness_json = updated
    flag_modified(row, "promotion_readiness_json")
    await db.flush()

    await record_official_speaking_promotion_event(
        db,
        student_id=student_id,
        language_id=language_id,
        payload_json={
            "old_cefr": old_cefr,
            "new_cefr": target,
            "assessment_id": aid,
            "attempt_id": attempt_key,
            "promoted_at": promoted_at,
        },
    )

    return SpeakingOfficialPromotionResult(
        success=True,
        old_cefr=old_cefr,
        new_cefr=target,
        reason="Official speaking CEFR promoted. You are ready for your new-level journey.",
        assessment_id=aid,
        attempt_id=attempt_key,
        promoted_at=promoted_at,
        already_promoted=False,
        ready_for_new_journey=True,
    )
