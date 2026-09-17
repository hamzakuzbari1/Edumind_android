"""Typed live-budget errors — product-safe codes, no provider leakage."""

from __future__ import annotations


class LiveBudgetError(Exception):
    """Base for S13 budget / lease failures."""

    code: str = "budget_error"
    student_message: str = "Talk with Alex is unavailable right now. Please try again."

    def __init__(self, message: str | None = None, *, detail: str = "") -> None:
        super().__init__(message or self.student_message)
        self.detail = detail


class DailyLimitReachedError(LiveBudgetError):
    code = "daily_limit_reached"
    student_message = (
        "You've used today's Talk with Alex time. More time will be available tomorrow."
    )


class ConversationAlreadyActiveError(LiveBudgetError):
    code = "conversation_already_active"
    student_message = (
        "You already have an active Talk with Alex conversation. "
        "Finish it in your other tab, or wait a moment and try again."
    )


class InvalidOrExpiredLiveLeaseError(LiveBudgetError):
    code = "invalid_or_expired_live_lease"
    student_message = "This Talk with Alex session is no longer valid. Please start again."


class LiveLeaseNotOwnedError(LiveBudgetError):
    code = "live_lease_not_owned"
    student_message = "This Talk with Alex session is not available."


class BudgetStateUnavailableError(LiveBudgetError):
    code = "budget_state_unavailable"
    student_message = "Talk with Alex time could not be loaded right now. Please try again."
