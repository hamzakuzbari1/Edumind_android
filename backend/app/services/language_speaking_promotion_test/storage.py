"""Bounded SPA blueprint persistence under promotion_readiness_json (S18).

CORRECTION 1: Persist only active_blueprint + most_recent_terminal_blueprint.
Never accumulate an unbounded blueprints_by_id archive.
"""

from __future__ import annotations

from typing import Any

from app.services.language_speaking_promotion_test.policy import MAX_PERSISTED_BLUEPRINTS
from app.services.language_speaking_promotion_test.types import (
    SpaBlueprintStatus,
    SpeakingPromotionAssessmentBlueprint,
)

SPEAKING_PROMOTION_ASSESSMENTS_KEY = "speaking_promotion_assessments"

_TERMINAL_STATUSES = frozenset(
    {
        SpaBlueprintStatus.completed.value,
        SpaBlueprintStatus.abandoned.value,
        SpaBlueprintStatus.unavailable.value,
    }
)


def empty_assessments_bucket() -> dict[str, Any]:
    return {
        "active_blueprint": None,
        "most_recent_terminal_blueprint": None,
    }


def assessments_bucket_from_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return empty_assessments_bucket()
    raw = payload.get(SPEAKING_PROMOTION_ASSESSMENTS_KEY)
    if not isinstance(raw, dict):
        return empty_assessments_bucket()
    return {
        "active_blueprint": raw.get("active_blueprint") if isinstance(raw.get("active_blueprint"), dict) else None,
        "most_recent_terminal_blueprint": (
            raw.get("most_recent_terminal_blueprint")
            if isinstance(raw.get("most_recent_terminal_blueprint"), dict)
            else None
        ),
    }


def merge_assessments_into_payload(
    payload: dict[str, Any] | None,
    bucket: dict[str, Any],
) -> dict[str, Any]:
    out = dict(payload) if isinstance(payload, dict) else {}
    # Strip any accidental unbounded archives.
    clean = {
        "active_blueprint": bucket.get("active_blueprint"),
        "most_recent_terminal_blueprint": bucket.get("most_recent_terminal_blueprint"),
    }
    out[SPEAKING_PROMOTION_ASSESSMENTS_KEY] = clean
    return out


def count_persisted_blueprints(bucket: dict[str, Any]) -> int:
    n = 0
    if isinstance(bucket.get("active_blueprint"), dict):
        n += 1
    if isinstance(bucket.get("most_recent_terminal_blueprint"), dict):
        n += 1
    return n


def assert_bucket_bounded(bucket: dict[str, Any]) -> None:
    """Raise if the JSONB SPA collection is unbounded or exceeds retention policy."""
    if "blueprints_by_id" in bucket and bucket["blueprints_by_id"]:
        raise ValueError("unbounded blueprints_by_id is forbidden in S18 SPA persistence")
    if count_persisted_blueprints(bucket) > MAX_PERSISTED_BLUEPRINTS:
        raise ValueError(
            f"SPA blueprint retention exceeded bound of {MAX_PERSISTED_BLUEPRINTS}"
        )
    # Forbid list archives
    for key, val in bucket.items():
        if key in ("active_blueprint", "most_recent_terminal_blueprint"):
            continue
        if isinstance(val, (list, dict)) and val:
            raise ValueError(f"unexpected SPA archive key '{key}' — retention must stay bounded")


def get_active_blueprint(payload: dict[str, Any] | None) -> SpeakingPromotionAssessmentBlueprint | None:
    bucket = assessments_bucket_from_payload(payload)
    raw = bucket.get("active_blueprint")
    if not isinstance(raw, dict):
        return None
    return SpeakingPromotionAssessmentBlueprint.from_dict(raw)


def persist_active_blueprint(
    payload: dict[str, Any] | None,
    blueprint: SpeakingPromotionAssessmentBlueprint,
    *,
    retire_previous_active_as_terminal: bool = True,
) -> dict[str, Any]:
    """Store blueprint as active; optionally move previous active → most_recent_terminal.

    Retention remains ≤2 blueprints at all times.
    """
    bucket = assessments_bucket_from_payload(payload)
    previous = bucket.get("active_blueprint")
    if retire_previous_active_as_terminal and isinstance(previous, dict):
        prev_status = str(previous.get("status") or "")
        # Replace not_started/available without growing history beyond most_recent_terminal.
        if prev_status in _TERMINAL_STATUSES or prev_status in (
            SpaBlueprintStatus.not_started.value,
            SpaBlueprintStatus.available.value,
        ):
            bucket["most_recent_terminal_blueprint"] = previous
    bucket["active_blueprint"] = blueprint.to_dict()
    assert_bucket_bounded(bucket)
    return merge_assessments_into_payload(payload, bucket)


def mark_active_terminal(
    payload: dict[str, Any] | None,
    *,
    status: SpaBlueprintStatus,
) -> dict[str, Any]:
    """Move active → most_recent_terminal with terminal status (S19-ready helper)."""
    bucket = assessments_bucket_from_payload(payload)
    active = bucket.get("active_blueprint")
    if not isinstance(active, dict):
        return merge_assessments_into_payload(payload, bucket)
    terminal = dict(active)
    terminal["status"] = status.value
    bucket["most_recent_terminal_blueprint"] = terminal
    bucket["active_blueprint"] = None
    assert_bucket_bounded(bucket)
    return merge_assessments_into_payload(payload, bucket)
