"""Token-saving gate for on-demand AI content generation.

Two jobs:
  1. Generate only when the fresh-AI pool is exhausted (callers check the pool first) — most opens
     serve existing content for free.
  2. Circuit breaker: after a generation failure (e.g. Gemini quota/credits depleted), pause further
     attempts for a cooldown so we don't burn time/quota hammering a down service. Auto-resumes.
"""

from __future__ import annotations

import time

COOLDOWN_SECONDS = 300.0  # 5 min back-off after a failed generation
_state = {"paused_until": 0.0}


def can_generate(*, now: float | None = None) -> bool:
    """True unless we're in the post-failure cooldown."""
    now = time.time() if now is None else now
    return now >= _state["paused_until"]


def note_failure(*, now: float | None = None) -> None:
    """Generation failed (quota/credits/error) — back off for the cooldown."""
    now = time.time() if now is None else now
    _state["paused_until"] = now + COOLDOWN_SECONDS


def note_success() -> None:
    """Generation worked — clear any back-off."""
    _state["paused_until"] = 0.0


def seconds_until_retry(*, now: float | None = None) -> float:
    """Seconds until generation gate re-opens (0 if already open)."""
    now = time.time() if now is None else now
    remaining = _state["paused_until"] - now
    return max(0.0, remaining)
