"""Types for language_speaking_interruption (S0 stub)."""

from __future__ import annotations

from dataclasses import dataclass

LANGUAGE_SPEAKING_INTERRUPTION_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class InterruptionPolicyResult:
    """Placeholder contract — implemented in later phases."""

    stub: bool = True
    version: str = "0.1.0"
