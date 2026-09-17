"""JSONB helpers for speaking official promotions + SPA consume (S20)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.language_speaking_official_promotion.types import (
    MAX_PROMOTED_IDS,
    MAX_PROMOTION_EVENTS,
    SPEAKING_OFFICIAL_PROMOTIONS_KEY,
)
from app.services.language_speaking_promotion_test.execution_types import (
    SpaAssessmentOutcome,
    SpeakingPromotionAssessment,
)
from app.services.language_speaking_promotion_test.storage import (
    assessments_bucket_from_payload,
    merge_assessments_into_payload,
)

# Soft projection key owned by S17 readiness; mutated here only to clear SPA unlock
# after official promote (no import of language_speaking_promotion_readiness).
_SPEAKING_PROMOTION_KEY = "speaking_promotion"


def _speaking_promotion_bucket_from_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    raw = payload.get(_SPEAKING_PROMOTION_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def _merge_speaking_promotion_into_payload(
    payload: dict[str, Any] | None,
    bucket: dict[str, Any],
) -> dict[str, Any]:
    out = dict(payload) if isinstance(payload, dict) else {}
    out[_SPEAKING_PROMOTION_KEY] = dict(bucket)
    return out


def empty_promotions_bucket() -> dict[str, Any]:
    return {
        "events": [],
        "promoted_attempt_ids": [],
        "promoted_assessment_ids": [],
        "last_promotion": None,
    }


def promotions_bucket_from_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return empty_promotions_bucket()
    raw = payload.get(SPEAKING_OFFICIAL_PROMOTIONS_KEY)
    if not isinstance(raw, dict):
        return empty_promotions_bucket()
    return {
        "events": list(raw.get("events") or []) if isinstance(raw.get("events"), list) else [],
        "promoted_attempt_ids": (
            list(raw.get("promoted_attempt_ids") or [])
            if isinstance(raw.get("promoted_attempt_ids"), list)
            else []
        ),
        "promoted_assessment_ids": (
            list(raw.get("promoted_assessment_ids") or [])
            if isinstance(raw.get("promoted_assessment_ids"), list)
            else []
        ),
        "last_promotion": raw.get("last_promotion") if isinstance(raw.get("last_promotion"), dict) else None,
    }


def merge_promotions_into_payload(
    payload: dict[str, Any] | None,
    bucket: dict[str, Any],
) -> dict[str, Any]:
    out = dict(payload) if isinstance(payload, dict) else {}
    out[SPEAKING_OFFICIAL_PROMOTIONS_KEY] = {
        "events": list(bucket.get("events") or [])[-MAX_PROMOTION_EVENTS:],
        "promoted_attempt_ids": list(bucket.get("promoted_attempt_ids") or [])[-MAX_PROMOTED_IDS:],
        "promoted_assessment_ids": list(bucket.get("promoted_assessment_ids") or [])[-MAX_PROMOTED_IDS:],
        "last_promotion": bucket.get("last_promotion"),
    }
    return out


def is_attempt_already_promoted(payload: dict[str, Any] | None, attempt_id: str) -> bool:
    if not attempt_id:
        return False
    bucket = promotions_bucket_from_payload(payload)
    if attempt_id in {str(x) for x in bucket["promoted_attempt_ids"]}:
        return True
    for event in bucket["events"]:
        if isinstance(event, dict) and str(event.get("attempt_id")) == attempt_id:
            return True
    return False


def is_assessment_already_promoted(payload: dict[str, Any] | None, assessment_id: str) -> bool:
    if not assessment_id:
        return False
    bucket = promotions_bucket_from_payload(payload)
    if assessment_id in {str(x) for x in bucket["promoted_assessment_ids"]}:
        return True
    for event in bucket["events"]:
        if isinstance(event, dict) and str(event.get("assessment_id")) == assessment_id:
            return True
    return False


def assessment_raw_is_consumed(raw: dict[str, Any] | None) -> bool:
    if not isinstance(raw, dict):
        return False
    result = raw.get("result")
    if not isinstance(result, dict):
        return False
    return bool(result.get("consumed_by_promotion"))


def find_promotion_pass_assessment(
    payload: dict[str, Any] | None,
    *,
    assessment_id: str | None = None,
    attempt_id: str | None = None,
    include_consumed: bool = False,
) -> SpeakingPromotionAssessment | None:
    """Locate a PASS assessment eligible for official promotion (or matching ids)."""
    bucket = assessments_bucket_from_payload(payload)
    pairs: list[tuple[SpeakingPromotionAssessment, dict[str, Any]]] = []
    for key in ("active_assessment", "most_recent_terminal_assessment"):
        raw = bucket.get(key)
        if not isinstance(raw, dict):
            continue
        try:
            pairs.append((SpeakingPromotionAssessment.from_dict(raw), raw))
        except (KeyError, TypeError, ValueError):
            continue

    if assessment_id:
        pairs = [
            (a, raw)
            for a, raw in pairs
            if a.assessment_id == assessment_id or a.blueprint_id == assessment_id
        ]
    if attempt_id:
        filtered: list[tuple[SpeakingPromotionAssessment, dict[str, Any]]] = []
        for a, raw in pairs:
            cur = a.current_attempt.attempt_id if a.current_attempt else None
            hist_ids = {h.attempt_id for h in a.attempt_history}
            result_aid = a.result.attempt_id if a.result else None
            if attempt_id in {cur, result_aid} | hist_ids:
                filtered.append((a, raw))
        pairs = filtered

    for a, raw in pairs:
        if a.result is None:
            continue
        if a.result.outcome != SpaAssessmentOutcome.PASS:
            continue
        if not include_consumed and assessment_raw_is_consumed(raw):
            continue
        if attempt_id and a.result.attempt_id != attempt_id and (
            not a.current_attempt or a.current_attempt.attempt_id != attempt_id
        ):
            continue
        return a

    if assessment_id or attempt_id:
        return pairs[0][0] if pairs else None
    return None


def assessment_is_consumed(payload: dict[str, Any] | None, assessment_id: str) -> bool:
    bucket = assessments_bucket_from_payload(payload)
    for key in ("active_assessment", "most_recent_terminal_assessment"):
        raw = bucket.get(key)
        if not isinstance(raw, dict):
            continue
        if str(raw.get("assessment_id")) != assessment_id and str(raw.get("blueprint_id")) != assessment_id:
            continue
        return assessment_raw_is_consumed(raw)
    return False

def mark_assessment_consumed_in_payload(
    payload: dict[str, Any] | None,
    *,
    assessment_id: str,
    attempt_id: str,
    consumed_at: str | None = None,
) -> dict[str, Any]:
    """Mark SPA assessment consumed and clear session runtime (preserve history)."""
    ts = consumed_at or datetime.now(timezone.utc).isoformat()
    bucket = assessments_bucket_from_payload(payload)

    def _consume(raw: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(raw, dict):
            return raw
        if str(raw.get("assessment_id")) != assessment_id and str(raw.get("blueprint_id")) != assessment_id:
            return raw
        updated = dict(raw)
        updated["session"] = None
        result = dict(updated.get("result") or {})
        result["ready_for_official_promotion"] = False
        result["consumed_by_promotion"] = True
        result["consumed_at"] = ts
        if attempt_id:
            result["attempt_id"] = result.get("attempt_id") or attempt_id
        updated["result"] = result
        updated["updated_at"] = ts
        return updated

    bucket["active_assessment"] = _consume(bucket.get("active_assessment"))
    bucket["most_recent_terminal_assessment"] = _consume(bucket.get("most_recent_terminal_assessment"))

    # Prefer terminal slot for consumed PASS (clear active if it was the consumed one).
    active = bucket.get("active_assessment")
    if isinstance(active, dict) and (
        active.get("assessment_id") == assessment_id or active.get("blueprint_id") == assessment_id
    ):
        if isinstance(active.get("result"), dict) and active["result"].get("consumed_by_promotion"):
            bucket["most_recent_terminal_assessment"] = active
            bucket["active_assessment"] = None

    return merge_assessments_into_payload(payload, bucket)


def reset_speaking_promotion_readiness_projection(
    payload: dict[str, Any] | None,
    *,
    new_official_cefr: str,
) -> dict[str, Any]:
    """Clear SPA unlock soft projection after official promote — preserve internal history."""
    bucket = _speaking_promotion_bucket_from_payload(payload)
    readiness = dict(bucket.get("readiness") or {}) if isinstance(bucket.get("readiness"), dict) else {}
    # Soft-clear unlock; keep fingerprints/history if present for audit.
    readiness["spa_unlocked"] = False
    student = {
        "spa_unlocked": False,
        "official_cefr": new_official_cefr.upper(),
        "target_cefr": None,
        "message": "Begin your new-level speaking journey.",
        "status": "not_ready",
    }
    return _merge_speaking_promotion_into_payload(
        payload,
        {
            **bucket,
            "readiness": readiness,
            "student_projection": student,
        },
    )


def append_speaking_promotion_record(
    payload: dict[str, Any] | None,
    *,
    assessment_id: str,
    attempt_id: str,
    old_cefr: str,
    new_cefr: str,
    promoted_at: str | None = None,
) -> dict[str, Any]:
    ts = promoted_at or datetime.now(timezone.utc).isoformat()
    bucket = promotions_bucket_from_payload(payload)
    record = {
        "assessment_id": assessment_id,
        "attempt_id": attempt_id,
        "old_cefr": old_cefr.upper(),
        "new_cefr": new_cefr.upper(),
        "promoted_at": ts,
    }
    events = list(bucket["events"]) + [record]
    attempt_ids = list(dict.fromkeys([*bucket["promoted_attempt_ids"], attempt_id]))
    assessment_ids = list(dict.fromkeys([*bucket["promoted_assessment_ids"], assessment_id]))
    bucket = {
        "events": events[-MAX_PROMOTION_EVENTS:],
        "promoted_attempt_ids": attempt_ids[-MAX_PROMOTED_IDS:],
        "promoted_assessment_ids": assessment_ids[-MAX_PROMOTED_IDS:],
        "last_promotion": record,
    }
    return merge_promotions_into_payload(payload, bucket)


def last_promotion_for_attempt(
    payload: dict[str, Any] | None,
    attempt_id: str,
) -> dict[str, Any] | None:
    bucket = promotions_bucket_from_payload(payload)
    for event in reversed(bucket["events"]):
        if isinstance(event, dict) and str(event.get("attempt_id")) == attempt_id:
            return event
    last = bucket.get("last_promotion")
    if isinstance(last, dict) and str(last.get("attempt_id")) == attempt_id:
        return last
    return None
