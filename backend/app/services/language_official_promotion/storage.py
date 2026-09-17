"""Official promotion persistence (Phase 5.5).

Updates official_listening_cefr (+ overall when bottleneck requires).
Resets progression layer while preserving historical learning data.

POLICY: promote_listening_official_cefr is the only code path that mutates
official_listening_cefr at runtime. Callers must sync analytics.listening_level
after a successful promotion (see engine.apply_listening_official_promotion).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.progression import LanguageProgression
from app.services.language_level_utils import bottleneck_level
from app.services.language_official_promotion.types import PromotionTestAttemptRef


def _tests_bucket(payload: dict[str, Any]) -> dict[str, Any]:
    bucket = payload.get("listening_promotion_tests")
    if not isinstance(bucket, dict):
        return {"attempts": [], "used_lesson_ids": [], "used_sequences": []}
    bucket.setdefault("attempts", [])
    return bucket


def _promotions_bucket(payload: dict[str, Any]) -> dict[str, Any]:
    bucket = payload.get("listening_official_promotions")
    if not isinstance(bucket, dict):
        return {"events": [], "promoted_session_ids": []}
    bucket.setdefault("events", [])
    bucket.setdefault("promoted_session_ids", [])
    return bucket


def get_latest_promotion_test_attempt(payload: dict[str, Any] | None) -> PromotionTestAttemptRef | None:
    if not payload:
        return None
    attempts = _tests_bucket(payload).get("attempts") or []
    if not attempts:
        return None
    latest = attempts[-1]
    if not isinstance(latest, dict):
        return None
    return PromotionTestAttemptRef(
        session_id=str(latest.get("session_id", "")),
        attempt_number=int(latest.get("attempt_number", 0)),
        official_cefr=str(latest.get("official_cefr", "")),
        target_cefr=str(latest.get("target_cefr", "")),
        overall_score=float(latest.get("overall_score", 0.0)),
        result=str(latest.get("result", "")),
    )


def find_promotion_test_attempt(
    payload: dict[str, Any] | None,
    *,
    session_id: str,
) -> PromotionTestAttemptRef | None:
    if not payload:
        return None
    for attempt in reversed(_tests_bucket(payload).get("attempts") or []):
        if not isinstance(attempt, dict):
            continue
        if str(attempt.get("session_id")) == session_id:
            return PromotionTestAttemptRef(
                session_id=session_id,
                attempt_number=int(attempt.get("attempt_number", 0)),
                official_cefr=str(attempt.get("official_cefr", "")),
                target_cefr=str(attempt.get("target_cefr", "")),
                overall_score=float(attempt.get("overall_score", 0.0)),
                result=str(attempt.get("result", "")),
            )
    return None


def is_session_already_promoted(payload: dict[str, Any] | None, session_id: str) -> bool:
    if not payload:
        return False
    bucket = _promotions_bucket(payload)
    promoted = {str(sid) for sid in (bucket.get("promoted_session_ids") or [])}
    if session_id in promoted:
        return True
    for event in bucket.get("events") or []:
        if isinstance(event, dict) and str(event.get("session_id")) == session_id:
            return True
    return False


def build_journey_reset_payload(
    existing: dict[str, Any] | None,
    *,
    new_cefr: str,
    close_session_id: str | None,
) -> dict[str, Any]:
    """Reset progression layer; preserve exam, stability history, and promotion history."""
    existing = dict(existing or {})
    tests = dict(_tests_bucket(existing))
    if close_session_id:
        tests["active_session_id"] = None
        tests["last_closed_session_id"] = close_session_id
    stability = dict(existing.get("stability") or {})
    preserved_history = list(stability.get("history") or [])
    promotions = dict(_promotions_bucket(existing))

    return {
        "skill": "listening",
        "official_cefr": new_cefr.upper(),
        "readiness_score": 0,
        "status": "NOT_READY",
        "estimated_remaining": 1.0,
        "primary_blockers": ["Begin your new-level listening journey from Beginner stage."],
        "secondary_blockers": [],
        "strengths": [],
        "next_actions": ["Complete your first listening lesson at the new official level."],
        "persistent_stage": 1,
        "stage_score": 0,
        "gate_overall_score": 0.0,
        "gate_eligible": False,
        "dimensions": [],
        "stability": {
            "skill": "listening",
            "promotion_confidence": 0,
            "readiness_stability": 0.0,
            "rolling_average": 0.0,
            "rolling_minimum": 0.0,
            "rolling_variance": 0.0,
            "stable_lessons": 0,
            "current_streak": 0,
            "best_streak": int(stability.get("best_streak") or 0),
            "last_readiness_scores": [],
            "smoothed_readiness": 0.0,
            "prediction": "Not Ready",
            "recommendation": "New promotion cycle — rebuild readiness at the new official level.",
            "recommendations": ["Complete beginner-stage lessons before targeting the next gate."],
            "history": preserved_history,
        },
        "listening_promotion_tests": tests,
        "listening_official_promotions": promotions,
        "journey_reset_at": datetime.now(timezone.utc).isoformat(),
        "transition_gate_reset": True,
    }


async def promote_listening_official_cefr(
    row: LanguageProgression,
    *,
    new_listening: LanguageLevel,
) -> tuple[str, str, bool]:
    """Update only listening + overall (when bottleneck logic requires)."""
    old_listening = row.official_listening_cefr.value
    previous_overall = row.official_overall_cefr.value
    row.official_listening_cefr = new_listening
    level_map = {
        "reading": row.official_reading_cefr.value,
        "listening": new_listening.value,
        "writing": row.official_writing_cefr.value,
        "speaking": row.official_speaking_cefr.value,
    }
    new_overall = bottleneck_level(level_map) or new_listening
    overall_updated = new_overall.value != previous_overall
    row.official_overall_cefr = new_overall
    row.learning_stage_listening = 1
    row.promotion_readiness_score = 0
    row.last_promotion_at = datetime.now(timezone.utc)
    row.version = int(row.version or 0) + 1
    return previous_overall, new_overall.value, overall_updated


async def append_promotion_record(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    event_id: int | None,
    attempt: PromotionTestAttemptRef,
    telemetry_snapshot: dict[str, Any],
    journey_reset: dict[str, Any],
    locked_row: LanguageProgression | None = None,
) -> dict[str, Any] | None:
    from app.services.language_listening_progression.json_mutation import mutate_listening_progression_json

    def mutator(payload: dict) -> dict[str, Any] | None:
        if is_session_already_promoted(payload, attempt.session_id):
            return None

        updated = build_journey_reset_payload(
            payload,
            new_cefr=attempt.target_cefr,
            close_session_id=attempt.session_id,
        )
        promotions = _promotions_bucket(updated)
        record = {
            "event_id": event_id,
            "session_id": attempt.session_id,
            "attempt_number": attempt.attempt_number,
            "old_cefr": attempt.official_cefr,
            "new_cefr": attempt.target_cefr,
            "promotion_test_score": attempt.overall_score,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "promotion_reason": "Promotion test PASS",
            "telemetry": telemetry_snapshot,
            "journey_reset": journey_reset,
        }
        promotions["events"] = (promotions.get("events") or [])[-49:] + [record]
        promoted_ids = list(promotions.get("promoted_session_ids") or [])
        if attempt.session_id not in promoted_ids:
            promoted_ids.append(attempt.session_id)
        promotions["promoted_session_ids"] = promoted_ids[-100:]
        updated["listening_official_promotions"] = promotions
        payload.clear()
        payload.update(updated)
        return record

    _row, record = await mutate_listening_progression_json(
        db,
        student_id=student_id,
        language_id=language_id,
        mutator=mutator,
        locked_row=locked_row,
    )
    return record


async def resolve_recommended_next_listening_lesson(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    level: str,
) -> str | None:
    try:
        cefr = LanguageLevel(level.upper())
    except ValueError:
        return None
    result = await db.execute(
        select(LanguageContentItem.title, LanguageContentItem.id)
        .where(
            LanguageContentItem.language_id == language_id,
            LanguageContentItem.skill == LanguageSkill.listening,
            LanguageContentItem.content_type == "lesson",
            LanguageContentItem.level == cefr,
            LanguageContentItem.is_published.is_(True),
        )
        .order_by(LanguageContentItem.sort_order, LanguageContentItem.id)
        .limit(1)
    )
    row = result.first()
    if row is None:
        return f"Listening lesson at {cefr.value} (catalog pending)"
    return str(row[0])
