"""Server-authoritative live budget authorization and lease accounting (S13).

Usage is derived from server timestamps under an active lease — never from
client-reported duration, turn counts, audio chunks, or token counts.

READING the budget (read_daily_budget) NEVER creates or starts a lease.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_speaking_live_budget.errors import (
    BudgetStateUnavailableError,
    ConversationAlreadyActiveError,
    DailyLimitReachedError,
    InvalidOrExpiredLiveLeaseError,
    LiveLeaseNotOwnedError,
)
from app.services.language_speaking_live_budget.policy import (
    DAILY_LIMIT_SECONDS,
    HEARTBEAT_MAX_CHARGE_SECONDS,
    MAX_SESSION_SECONDS,
    POLICY_VERSION,
    STALE_LEASE_SECONDS,
    clamp_consumed,
    next_reset_at_utc,
    usage_date_utc,
    utc_now,
)
from app.services.language_speaking_live_budget.repository import (
    create_lease,
    get_active_lease_for_student,
    get_daily_usage,
    get_lease_by_id,
    list_stale_active_leases,
    lock_or_create_daily_usage,
)
from app.services.language_speaking_live_budget.types import (
    HeartbeatResult,
    LiveAuthorization,
    LiveBudgetState,
    LiveSessionEndResult,
)


def _parse_lease_id(raw: str | None) -> uuid.UUID | None:
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw).strip())
    except (ValueError, TypeError, AttributeError):
        return None


def _budget_state(
    *,
    consumed: int,
    now: datetime,
    session_cap: int | None = None,
) -> LiveBudgetState:
    consumed_c = clamp_consumed(consumed)
    remaining = max(0, DAILY_LIMIT_SECONDS - consumed_c)
    if session_cap is None:
        allowed = min(remaining, MAX_SESSION_SECONDS)
    else:
        allowed = max(0, min(remaining, session_cap, MAX_SESSION_SECONDS))
    reset = next_reset_at_utc(now)
    return LiveBudgetState(
        daily_limit_seconds=DAILY_LIMIT_SECONDS,
        consumed_seconds=consumed_c,
        remaining_seconds=remaining,
        session_allowed_seconds=allowed,
        reset_at_utc=reset.isoformat().replace("+00:00", "Z"),
        available=True,
        policy_version=POLICY_VERSION,
        usage_date=usage_date_utc(now).isoformat(),
    )


def _charge_delta(
    *,
    lease_accounted: int,
    last_heartbeat_at: datetime,
    now: datetime,
    deadline_at: datetime,
    daily_consumed: int,
) -> int:
    """Server-derived charge since last heartbeat, bounded and capped."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=last_heartbeat_at.tzinfo)
    elapsed = int((now - last_heartbeat_at).total_seconds())
    if elapsed <= 0:
        return 0
    elapsed = min(elapsed, HEARTBEAT_MAX_CHARGE_SECONDS)

    # Never charge past the lease deadline (hard session bound).
    until_deadline = int((deadline_at - last_heartbeat_at).total_seconds())
    if until_deadline <= 0:
        return 0
    elapsed = min(elapsed, until_deadline)

    # Never charge more than the lease itself can hold (MAX_SESSION_SECONDS).
    lease_room = max(0, MAX_SESSION_SECONDS - lease_accounted)
    elapsed = min(elapsed, lease_room)

    # Never exceed the daily policy in persisted accounting.
    daily_room = max(0, DAILY_LIMIT_SECONDS - daily_consumed)
    return min(elapsed, daily_room)


async def reconcile_stale_leases(
    db: AsyncSession,
    *,
    student_id: int,
    now: datetime | None = None,
) -> int:
    """Expire abandoned leases; charge only up to last_heartbeat + max interval.

    Prevents zombie leases from consuming the student's entire future budget.
    Returns total seconds charged during reconciliation.
    """
    ts = now or utc_now()
    stale_before = ts - timedelta(seconds=STALE_LEASE_SECONDS)
    # Also treat past-deadline leases as stale regardless of heartbeat age.
    active = await get_active_lease_for_student(db, student_id=student_id, for_update=True)
    charged_total = 0
    leases = []
    if active is not None:
        leases.append(active)
    # Include any additional stale rows (defensive for malformed multi-active).
    for extra in await list_stale_active_leases(
        db, student_id=student_id, stale_before=stale_before, for_update=True
    ):
        if all(extra.id != x.id for x in leases):
            leases.append(extra)

    for lease in leases:
        is_stale = lease.last_heartbeat_at < stale_before or lease.deadline_at <= ts
        if not is_stale:
            continue
        day = lease.usage_date
        usage = await lock_or_create_daily_usage(
            db, student_id=student_id, usage_date=day, now=ts
        )
        # Bound: charge at most one heartbeat-max interval past last heartbeat,
        # and never past deadline.
        charge_until = min(
            lease.last_heartbeat_at + timedelta(seconds=HEARTBEAT_MAX_CHARGE_SECONDS),
            lease.deadline_at,
            ts,
        )
        delta = _charge_delta(
            lease_accounted=lease.accounted_seconds,
            last_heartbeat_at=lease.last_heartbeat_at,
            now=charge_until,
            deadline_at=lease.deadline_at,
            daily_consumed=usage.consumed_seconds,
        )
        if delta > 0:
            lease.accounted_seconds = lease.accounted_seconds + delta
            usage.consumed_seconds = clamp_consumed(usage.consumed_seconds + delta)
            usage.updated_at = ts
            charged_total += delta
        lease.status = "expired"
        lease.updated_at = ts
        lease.last_heartbeat_at = charge_until

    await db.flush()
    return charged_total


async def read_daily_budget(
    db: AsyncSession,
    *,
    student_id: int,
    now: datetime | None = None,
) -> LiveBudgetState:
    """Authoritative remaining seconds — READ ONLY. Never starts a lease."""
    try:
        ts = now or utc_now()
        await reconcile_stale_leases(db, student_id=student_id, now=ts)
        day = usage_date_utc(ts)
        usage = await get_daily_usage(db, student_id=student_id, usage_date=day)
        consumed = int(usage.consumed_seconds) if usage is not None else 0
        return _budget_state(consumed=consumed, now=ts)
    except BudgetStateUnavailableError:
        raise
    except Exception as exc:
        raise BudgetStateUnavailableError(detail=str(exc)) from exc


async def authorize_live_session(
    db: AsyncSession,
    *,
    student_id: int,
    continuity_lease_id: str | None = None,
    now: datetime | None = None,
) -> LiveAuthorization:
    """Create or resume the authoritative live lease; gate on remaining budget.

    Concurrent-tab rule: at most one active lease per student. A second tab
    without the same continuity lease_id is denied as conversation_already_active.
    Invalid continuity does NOT silently mint a new lease.
    """
    ts = now or utc_now()
    day = usage_date_utc(ts)
    await reconcile_stale_leases(db, student_id=student_id, now=ts)

    usage = await lock_or_create_daily_usage(
        db, student_id=student_id, usage_date=day, now=ts
    )
    remaining = max(0, DAILY_LIMIT_SECONDS - int(usage.consumed_seconds))
    if remaining <= 0:
        raise DailyLimitReachedError()

    continuity = _parse_lease_id(continuity_lease_id)
    active = await get_active_lease_for_student(db, student_id=student_id, for_update=True)

    if active is not None:
        if continuity is not None and active.id == continuity:
            # Resume same logical conversation — no reset, no double charge.
            if active.deadline_at <= ts:
                raise InvalidOrExpiredLiveLeaseError(detail="deadline_passed")
            lease_remaining = max(
                0, int((active.deadline_at - ts).total_seconds())
            )
            budget = _budget_state(
                consumed=int(usage.consumed_seconds),
                now=ts,
                session_cap=lease_remaining,
            )
            if budget.remaining_seconds <= 0 or budget.session_allowed_seconds <= 0:
                raise DailyLimitReachedError()
            active.last_heartbeat_at = ts
            active.updated_at = ts
            await db.flush()
            return LiveAuthorization(
                lease_id=str(active.id),
                resumed=True,
                budget=budget,
            )
        if continuity is not None and active.id != continuity:
            # Explicit wrong continuity — do not silently mint.
            raise InvalidOrExpiredLiveLeaseError(detail="continuity_mismatch")
        # No continuity (or empty) while another lease is active -> multi-tab.
        raise ConversationAlreadyActiveError(detail=str(active.id))

    if continuity is not None:
        # Client claims continuity but no active lease — fail closed.
        existing = await get_lease_by_id(db, lease_id=continuity, for_update=True)
        if existing is None or existing.student_id != student_id:
            raise InvalidOrExpiredLiveLeaseError(detail="unknown_lease")
        raise InvalidOrExpiredLiveLeaseError(detail="lease_not_active")

    allowed = min(remaining, MAX_SESSION_SECONDS)
    deadline = ts + timedelta(seconds=allowed)
    lease = create_lease(
        student_id=student_id,
        usage_date=day,
        started_at=ts,
        deadline_at=deadline,
    )
    db.add(lease)
    await db.flush()
    budget = _budget_state(consumed=int(usage.consumed_seconds), now=ts, session_cap=allowed)
    return LiveAuthorization(
        lease_id=str(lease.id),
        resumed=False,
        budget=budget,
    )


async def validate_active_lease(
    db: AsyncSession,
    *,
    student_id: int,
    lease_id: str,
    now: datetime | None = None,
) -> bool:
    """Read-only ownership/liveness check for an authorization boundary.

    Returns True only when the lease exists, is owned by ``student_id``, is still
    ``active``, and has not passed its deadline. Never charges, never mints.
    Used by S14 to gate live-turn execution before any S8 mutation.
    """
    ts = now or utc_now()
    lid = _parse_lease_id(lease_id)
    if lid is None:
        return False
    lease = await get_lease_by_id(db, lease_id=lid)
    if lease is None:
        return False
    if lease.student_id != student_id:
        return False
    if lease.status != "active":
        return False
    if lease.deadline_at <= ts:
        return False
    return True


async def heartbeat_live_session(
    db: AsyncSession,
    *,
    student_id: int,
    lease_id: str,
    now: datetime | None = None,
) -> HeartbeatResult:
    """Advance accounting from server elapsed time. Client must NOT send duration."""
    ts = now or utc_now()
    lid = _parse_lease_id(lease_id)
    if lid is None:
        raise InvalidOrExpiredLiveLeaseError(detail="malformed_lease_id")

    lease = await get_lease_by_id(db, lease_id=lid, for_update=True)
    if lease is None:
        raise InvalidOrExpiredLiveLeaseError(detail="unknown_lease")
    if lease.student_id != student_id:
        raise LiveLeaseNotOwnedError(detail="cross_student")
    if lease.status != "active":
        raise InvalidOrExpiredLiveLeaseError(detail="lease_not_active")

    usage = await lock_or_create_daily_usage(
        db, student_id=student_id, usage_date=lease.usage_date, now=ts
    )

    deadline_reached = ts >= lease.deadline_at
    charge_until = min(ts, lease.deadline_at)
    delta = _charge_delta(
        lease_accounted=lease.accounted_seconds,
        last_heartbeat_at=lease.last_heartbeat_at,
        now=charge_until,
        deadline_at=lease.deadline_at,
        daily_consumed=usage.consumed_seconds,
    )
    if delta > 0:
        lease.accounted_seconds = lease.accounted_seconds + delta
        usage.consumed_seconds = clamp_consumed(usage.consumed_seconds + delta)
        usage.updated_at = ts

    # Duplicate / near-zero heartbeat: still advance last_heartbeat to now
    # (or stay) but never reduce accounted/consumed.
    if not deadline_reached:
        lease.last_heartbeat_at = ts
    else:
        lease.last_heartbeat_at = lease.deadline_at
        lease.status = "ended"
    lease.updated_at = ts
    await db.flush()

    remaining_on_lease = max(0, int((lease.deadline_at - ts).total_seconds()))
    budget = _budget_state(
        consumed=int(usage.consumed_seconds),
        now=ts,
        session_cap=remaining_on_lease if lease.status == "active" else 0,
    )
    return HeartbeatResult(
        lease_id=str(lease.id),
        charged_seconds=delta,
        lease_accounted_seconds=lease.accounted_seconds,
        budget=budget,
        deadline_reached=deadline_reached or budget.remaining_seconds <= 0,
    )


async def end_live_session(
    db: AsyncSession,
    *,
    student_id: int,
    lease_id: str,
    now: datetime | None = None,
) -> LiveSessionEndResult:
    """Intentional end — final reconcile of server-elapsed time, mark ended."""
    ts = now or utc_now()
    lid = _parse_lease_id(lease_id)
    if lid is None:
        raise InvalidOrExpiredLiveLeaseError(detail="malformed_lease_id")

    lease = await get_lease_by_id(db, lease_id=lid, for_update=True)
    if lease is None:
        raise InvalidOrExpiredLiveLeaseError(detail="unknown_lease")
    if lease.student_id != student_id:
        raise LiveLeaseNotOwnedError(detail="cross_student")

    usage = await lock_or_create_daily_usage(
        db, student_id=student_id, usage_date=lease.usage_date, now=ts
    )
    delta = 0
    if lease.status == "active":
        charge_until = min(ts, lease.deadline_at)
        delta = _charge_delta(
            lease_accounted=lease.accounted_seconds,
            last_heartbeat_at=lease.last_heartbeat_at,
            now=charge_until,
            deadline_at=lease.deadline_at,
            daily_consumed=usage.consumed_seconds,
        )
        if delta > 0:
            lease.accounted_seconds = lease.accounted_seconds + delta
            usage.consumed_seconds = clamp_consumed(usage.consumed_seconds + delta)
            usage.updated_at = ts
        lease.status = "ended"
        lease.last_heartbeat_at = charge_until
        lease.updated_at = ts
        await db.flush()

    budget = _budget_state(consumed=int(usage.consumed_seconds), now=ts, session_cap=0)
    return LiveSessionEndResult(
        lease_id=str(lease.id),
        charged_seconds=delta,
        budget=budget,
    )
