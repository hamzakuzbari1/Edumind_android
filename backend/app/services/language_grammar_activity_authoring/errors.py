"""Activity Authoring errors (V1.3)."""

from __future__ import annotations


class ActivityAuthoringError(ValueError):
    """Base authoring error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class AuthoringValidationError(ActivityAuthoringError):
    """Invalid authoring request."""


class AuthoringStrategyError(ActivityAuthoringError):
    """Missing or incompatible authoring strategy."""
