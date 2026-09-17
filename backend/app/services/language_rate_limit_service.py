"""Phase 12 — per-user rate limiting for expensive AI calls.

In-memory sliding-window limiter (single-process; swap the store for Redis at multi-instance scale).
Keeps a learner from hammering costly AI endpoints. Placement security categories fail closed on an
internal limiter error; established non-placement learning categories retain their fail-open behavior.
"""

from __future__ import annotations

import time
from math import ceil
from threading import Lock

from fastapi import HTTPException, status

from app.core.config import get_settings

# category -> (max_calls, window_seconds)
_DEFAULT_RATE_LIMITS: dict[str, tuple[int, float]] = {
    "gemini": (60, 60.0),     # general AI calls
    "speaking": (20, 60.0),   # audio turns (heavier)
    "lesson_gen": (10, 60.0), # on-demand content generation
    "placement_start": (5, 60.0),
    "placement_audio_turn": (10, 60.0),
    "placement_answer": (60, 60.0),
    "placement_poll": (60, 60.0),
    "placement_abandon": (5, 60.0),
    "placement_generation": (3, 300.0),
    "placement_evaluation": (3, 300.0),
    "placement_evaluation_request": (3, 300.0),
}


def _configured_limits(raw: str) -> dict[str, tuple[int, float]]:
    """Parse safe environment overrides in the form ``category=limit/window``."""
    parsed: dict[str, tuple[int, float]] = {}
    for item in (raw or "").split(","):
        item = item.strip()
        if not item or "=" not in item or "/" not in item:
            continue
        category, value = item.split("=", 1)
        limit_raw, window_raw = value.split("/", 1)
        category = category.strip()
        if category not in _DEFAULT_RATE_LIMITS or not category.startswith("placement_"):
            continue
        try:
            limit = int(limit_raw)
            window = float(window_raw)
        except ValueError:
            continue
        if 1 <= limit <= 10_000 and 1.0 <= window <= 86_400.0:
            parsed[category] = (limit, window)
    return parsed


RATE_LIMITS: dict[str, tuple[int, float]] = dict(_DEFAULT_RATE_LIMITS)
RATE_LIMITS.update(_configured_limits(get_settings().LANGUAGE_PLACEMENT_RATE_LIMITS))

# key -> list[timestamps]
_hits: dict[str, list[float]] = {}
_hits_lock = Lock()
_last_cleanup_at = 0.0


def within_limit(timestamps: list[float], *, limit: int, window: float, now: float) -> tuple[bool, list[float]]:
    """Pure check: keep only timestamps inside the window; allow when below the limit.

    Returns (allowed, pruned_timestamps_including_now_if_allowed)."""
    cutoff = now - window
    recent = [t for t in timestamps if t > cutoff]
    if len(recent) >= limit:
        return False, recent
    recent.append(now)
    return True, recent


def _cleanup_expired_keys(now: float) -> None:
    """Bound process-local bucket memory; caller must hold ``_hits_lock``."""
    global _last_cleanup_at
    cleanup_interval = max(1, int(get_settings().LANGUAGE_RATE_LIMIT_CLEANUP_SECONDS))
    if now >= _last_cleanup_at and now - _last_cleanup_at < cleanup_interval:
        return
    _last_cleanup_at = now
    for key in list(_hits):
        category = key.split(":", 1)[0]
        configured = RATE_LIMITS.get(category)
        if not configured:
            del _hits[key]
            continue
        _, window = configured
        recent = [timestamp for timestamp in _hits[key] if timestamp > now - window]
        if recent:
            _hits[key] = recent
        else:
            del _hits[key]


def _check_with_retry_after(category: str, identifier) -> tuple[bool, int]:
    """Record a hit and return ``(allowed, seconds_until_oldest_hit_expires)``."""
    try:
        limit, window = RATE_LIMITS[category]
        key = f"{category}:{identifier}"
        now = time.time()
        with _hits_lock:
            _cleanup_expired_keys(now)
            allowed, recent = within_limit(_hits.get(key, []), limit=limit, window=window, now=now)
            _hits[key] = recent
            retry_after = max(1, ceil((recent[0] + window) - now)) if not allowed and recent else 1
        return allowed, retry_after
    except Exception:
        # Placement endpoints fail closed. Established unrelated learning limits retain their
        # historical fail-open behavior.
        return (not category.startswith("placement_"), 1)


def check(category: str, identifier) -> bool:
    """Stateful: record a hit for (category, identifier) and return whether it is allowed."""
    allowed, _ = _check_with_retry_after(category, identifier)
    return allowed


def check_or_raise(category: str, identifier) -> None:
    """Raise HTTP 429 when the per-user limit for this category is exceeded."""
    allowed, retry_after = _check_with_retry_after(category, identifier)
    if not allowed:
        limit, window = RATE_LIMITS.get(category, (0, 0.0))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limit_exceeded",
                "message": f"Too many requests; limit {limit} per {int(window)} seconds.",
            },
            headers={"Retry-After": str(retry_after)},
        )
