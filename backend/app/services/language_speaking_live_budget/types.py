"""S13 live budget value types — infrastructure, not educational authority."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LiveBudgetState:
    daily_limit_seconds: int
    consumed_seconds: int
    remaining_seconds: int
    session_allowed_seconds: int
    reset_at_utc: str
    available: bool
    policy_version: str
    usage_date: str

    def to_student_dict(self) -> dict[str, object]:
        return {
            "daily_limit_seconds": self.daily_limit_seconds,
            "consumed_seconds": self.consumed_seconds,
            "remaining_seconds": self.remaining_seconds,
            "session_allowed_seconds": self.session_allowed_seconds,
            "reset_at_utc": self.reset_at_utc,
            "available": self.available,
            "policy_version": self.policy_version,
            "usage_date": self.usage_date,
        }


@dataclass(frozen=True, slots=True)
class LiveAuthorization:
    lease_id: str
    resumed: bool
    budget: LiveBudgetState

    def to_student_dict(self) -> dict[str, object]:
        return {
            "lease_id": self.lease_id,
            "resumed": self.resumed,
            **self.budget.to_student_dict(),
        }


@dataclass(frozen=True, slots=True)
class HeartbeatResult:
    lease_id: str
    charged_seconds: int
    lease_accounted_seconds: int
    budget: LiveBudgetState
    deadline_reached: bool

    def to_student_dict(self) -> dict[str, object]:
        return {
            "lease_id": self.lease_id,
            "charged_seconds": self.charged_seconds,
            "lease_accounted_seconds": self.lease_accounted_seconds,
            "deadline_reached": self.deadline_reached,
            **self.budget.to_student_dict(),
        }


@dataclass(frozen=True, slots=True)
class LiveSessionEndResult:
    lease_id: str
    charged_seconds: int
    budget: LiveBudgetState

    def to_student_dict(self) -> dict[str, object]:
        return {
            "lease_id": self.lease_id,
            "charged_seconds": self.charged_seconds,
            **self.budget.to_student_dict(),
        }
