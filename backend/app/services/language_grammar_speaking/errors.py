"""Speaking Domain errors (V1.2A) — structured only."""

from __future__ import annotations


class SpeakingDomainError(ValueError):
    """Base Speaking domain error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class SpeakingValidationError(SpeakingDomainError):
    """Invalid session / attempt / turn / grammar targets."""


class SpeakingStateError(SpeakingDomainError):
    """Illegal lifecycle or state-machine transition."""


class SpeakingLifecycleError(SpeakingDomainError):
    """Lifecycle phase failure."""
