"""WPA persistence bucket."""

from __future__ import annotations

from typing import Any

WRITING_TESTS_KEY = "writing_promotion_tests"


def tests_bucket(payload: dict[str, Any]) -> dict[str, Any]:
    bucket = payload.get(WRITING_TESTS_KEY)
    if not isinstance(bucket, dict):
        return {"attempts": [], "active_session": None}
    bucket.setdefault("attempts", [])
    return bucket


def get_active_session(payload: dict[str, Any]) -> dict[str, Any] | None:
    raw = tests_bucket(payload).get("active_session")
    return raw if isinstance(raw, dict) else None


def latest_attempt(payload: dict[str, Any]) -> dict[str, Any] | None:
    attempts = tests_bucket(payload).get("attempts") or []
    if not attempts:
        return None
    last = attempts[-1]
    return last if isinstance(last, dict) else None
