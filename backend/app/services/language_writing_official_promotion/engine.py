"""Writing official promotion — sole runtime writer of official_writing_cefr."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.progression import LanguageProgression
from app.services.language_level_utils import bottleneck_level
from app.services.language_progression_service import get_official_cefr, record_progression_event
from app.services.language_writing.enums import OfficialWritingCEFR
from app.services.language_writing_learning_stage.types import WritingLearningStage, writing_stage_label
from app.services.language_writing_official_promotion.types import WritingOfficialPromotionResult
from app.services.language_writing_progression.locking import lock_writing_progression_row
from app.services.language_writing_progression.storage import WRITING_PROGRESSION_KEY, empty_writing_state
from app.services.language_writing_promotion_test.storage import WRITING_TESTS_KEY, latest_attempt, tests_bucket

PROMOTIONS_KEY = "writing_official_promotions"


def _promotions_bucket(payload: dict) -> dict:
    b = payload.get(PROMOTIONS_KEY)
    if not isinstance(b, dict):
        return {"events": [], "promoted_session_ids": []}
    b.setdefault("events", [])
    b.setdefault("promoted_session_ids", [])
    return b


def _build_writing_reset_payload(existing: dict, *, new_cefr: str) -> dict:
    tests = dict(tests_bucket(existing))
    tests["active_session"] = None
    stability = dict(existing.get("writing_stability") or {})
    preserved_history = list(stability.get("readiness_history") or [])
    promotions = dict(_promotions_bucket(existing))
    writing = empty_writing_state()
    writing["learning_stage"] = 1
    writing["learning_stage_label"] = writing_stage_label(official_cefr=new_cefr, stage=WritingLearningStage.beginner)
    writing["estimated_lessons_to_next_stage"] = 5
    return {
        **existing,
        "writing_readiness": {
            "skill": "writing",
            "official_cefr": new_cefr.upper(),
            "readiness_score": 0,
            "status": "NOT_READY",
            "estimated_remaining": 100.0,
            "primary_blockers": ["Begin your new-level writing journey from Beginner stage."],
            "secondary_blockers": [],
            "persistent_stage": 1,
            "stage_score": 0,
            "gate_overall_score": 0.0,
            "gate_eligible": False,
        },
        WRITING_PROGRESSION_KEY: writing,
        "writing_stability": {
            **stability,
            "readiness_history": preserved_history,
            "promotion_confidence": 0,
            "prediction": "Not Ready",
        },
        WRITING_TESTS_KEY: tests,
        PROMOTIONS_KEY: promotions,
        "writing_journey_reset_at": datetime.now(timezone.utc).isoformat(),
    }


async def apply_writing_official_promotion(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    session_id: str | None = None,
    locked_row: LanguageProgression | None = None,
) -> WritingOfficialPromotionResult:
    row = locked_row or await lock_writing_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        official = await get_official_cefr(db, student_id=student_id, language_id=language_id, skill="writing")
        return WritingOfficialPromotionResult(
            success=False,
            old_cefr=official.level.value,
            new_cefr=official.level.value,
            reason="No progression row found.",
        )
    payload = dict(row.promotion_readiness_json or {})
    attempt = latest_attempt(payload)
    if session_id:
        for a in reversed(tests_bucket(payload).get("attempts") or []):
            if isinstance(a, dict) and str(a.get("session_id")) == session_id:
                attempt = a
                break
    if attempt is None:
        return WritingOfficialPromotionResult(
            success=False,
            old_cefr=row.official_writing_cefr.value,
            new_cefr=row.official_writing_cefr.value,
            reason="No WPA attempt found.",
        )
    if str(attempt.get("result")) != "PASS":
        return WritingOfficialPromotionResult(
            success=False,
            old_cefr=row.official_writing_cefr.value,
            new_cefr=row.official_writing_cefr.value,
            reason=f"Promotion requires PASS (latest: {attempt.get('result')}).",
        )
    sid = str(attempt.get("session_id"))
    promoted_ids = set(_promotions_bucket(payload).get("promoted_session_ids") or [])
    old_cefr = row.official_writing_cefr.value
    new_cefr = str(attempt.get("target_cefr") or old_cefr).upper()
    if sid in promoted_ids:
        return WritingOfficialPromotionResult(success=True, old_cefr=old_cefr, new_cefr=new_cefr, reason="Already promoted.")
    try:
        new_level = LanguageLevel(new_cefr)
    except ValueError:
        return WritingOfficialPromotionResult(
            success=False, old_cefr=old_cefr, new_cefr=old_cefr, reason="Invalid target CEFR."
        )
    row.official_writing_cefr = new_level
    row.official_overall_cefr = (
        bottleneck_level(
            {
                "reading": row.official_reading_cefr,
                "listening": row.official_listening_cefr,
                "writing": new_level,
                "speaking": row.official_speaking_cefr,
            }
        )
        or new_level
    )
    row.learning_stage_writing = 1
    row.promotion_readiness_score = 0
    reset_payload = _build_writing_reset_payload(payload, new_cefr=new_cefr)
    prom = _promotions_bucket(reset_payload)
    prom["promoted_session_ids"] = list(promoted_ids | {sid})
    prom["events"] = list(prom.get("events") or []) + [
        {
            "session_id": sid,
            "old_cefr": old_cefr,
            "new_cefr": new_cefr,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    reset_payload[PROMOTIONS_KEY] = prom
    row.promotion_readiness_json = reset_payload
    flag_modified(row, "promotion_readiness_json")
    await db.flush()
    await record_progression_event(
        db,
        student_id=student_id,
        language_id=language_id,
        event_type="writing_official_promotion",
        payload_json={"old_cefr": old_cefr, "new_cefr": new_cefr, "session_id": sid},
        force=True,
    )
    return WritingOfficialPromotionResult(
        success=True,
        old_cefr=old_cefr,
        new_cefr=new_cefr,
        reason="Official writing CEFR promoted.",
        session_id=sid,
    )
