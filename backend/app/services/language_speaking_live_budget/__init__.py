"""Speaking Alex daily live budget (S13) — infrastructure cost-control ownership.

RESPONSIBILITY: Talk with Alex daily live budget policy, lease ownership,
usage accounting, and server-authoritative remaining time (cost control only).

Owns:
- daily live budget policy (600s / UTC calendar day)
- daily usage accounting
- session reservation / active lease ownership
- reconciliation
- server-authoritative remaining time
- concurrent live-session prevention

Must NOT import:
- evaluator, knowledge_bridge, knowledge_model
- progression, learning_stage, promotion readiness, official promotion
"""

from __future__ import annotations

from app.services.language_speaking_live_budget.accounting import (
    authorize_live_session,
    end_live_session,
    heartbeat_live_session,
    read_daily_budget,
    reconcile_stale_leases,
    validate_active_lease,
)
from app.services.language_speaking_live_budget.errors import (
    BudgetStateUnavailableError,
    ConversationAlreadyActiveError,
    DailyLimitReachedError,
    InvalidOrExpiredLiveLeaseError,
    LiveBudgetError,
    LiveLeaseNotOwnedError,
)
from app.services.language_speaking_live_budget.policy import (
    DAILY_LIMIT_SECONDS,
    HEARTBEAT_INTERVAL_SECONDS,
    HEARTBEAT_MAX_CHARGE_SECONDS,
    MAX_SESSION_SECONDS,
    POLICY_VERSION,
    STALE_LEASE_SECONDS,
    next_reset_at_utc,
    usage_date_utc,
)
from app.services.language_speaking_live_budget.types import (
    HeartbeatResult,
    LiveAuthorization,
    LiveBudgetState,
    LiveSessionEndResult,
)

__all__ = [
    "DAILY_LIMIT_SECONDS",
    "HEARTBEAT_INTERVAL_SECONDS",
    "HEARTBEAT_MAX_CHARGE_SECONDS",
    "MAX_SESSION_SECONDS",
    "POLICY_VERSION",
    "STALE_LEASE_SECONDS",
    "BudgetStateUnavailableError",
    "ConversationAlreadyActiveError",
    "DailyLimitReachedError",
    "HeartbeatResult",
    "InvalidOrExpiredLiveLeaseError",
    "LiveAuthorization",
    "LiveBudgetError",
    "LiveBudgetState",
    "LiveLeaseNotOwnedError",
    "LiveSessionEndResult",
    "authorize_live_session",
    "end_live_session",
    "heartbeat_live_session",
    "next_reset_at_utc",
    "read_daily_budget",
    "reconcile_stale_leases",
    "usage_date_utc",
    "validate_active_lease",
]
