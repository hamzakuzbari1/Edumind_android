"""S13 daily Talk-with-Alex live budget policy.

Daily reset boundary (deterministic, server-authoritative)
-----------------------------------------------------------
- Timezone: UTC only.
- Day boundary: 00:00:00 UTC.
- usage_date = datetime.now(timezone.utc).date()

Do not use browser local date, database session timezone, or naive
datetime.now() without tz. Mixing those would split or double-charge
the same physical day across students in different regions.

Hard enforcement honesty (Approach A)
-------------------------------------
The browser connects directly to Hume. The backend cannot force-close an
already-open browser->Hume WebSocket. S13 enforces:
1. Server-authoritative daily lease + accounting (monotonic, capped).
2. Budget gate before minting live credentials.
3. Bounded session_allowed_seconds returned to the client.
4. Cooperative frontend deadline auto-end.

A malicious client that keeps one socket open for the full provider token
TTL cannot be mid-session force-cut without a transport proxy (out of scope).
The *next* authorization is still gated on remaining budget.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

# Named versioned policy — bump when the product limit changes.
POLICY_VERSION = "s13.v1"

DAILY_LIMIT_SECONDS = 600
MAX_SESSION_SECONDS = 600

# Heartbeat: product range 10-20s. 15s balances cost vs accuracy.
HEARTBEAT_INTERVAL_SECONDS = 15
# Cap charge per heartbeat so a stalled/retrying client cannot leap-advance.
HEARTBEAT_MAX_CHARGE_SECONDS = 20

# A lease with no heartbeat for this long is stale and must be reconciled
# so it cannot zombie-consume the student's future budget.
STALE_LEASE_SECONDS = HEARTBEAT_INTERVAL_SECONDS * 3  # 45s


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def usage_date_utc(now: datetime | None = None) -> date:
    """Calendar day under the project UTC-only daily boundary."""
    ts = now if now is not None else utc_now()
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    else:
        ts = ts.astimezone(timezone.utc)
    return ts.date()


def next_reset_at_utc(now: datetime | None = None) -> datetime:
    """Next UTC midnight after ``usage_date_utc(now)``."""
    day = usage_date_utc(now)
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc) + timedelta(days=1)


def clamp_consumed(seconds: int) -> int:
    """Monotonic daily cap — never exceed the policy limit in persisted accounting."""
    return max(0, min(int(seconds), DAILY_LIMIT_SECONDS))
