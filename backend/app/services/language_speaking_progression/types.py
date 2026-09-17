"""Types for language_speaking_progression (S0 stub)."""

from __future__ import annotations

from dataclasses import dataclass

LANGUAGE_SPEAKING_PROGRESSION_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class SpeakingProgressionState:
    """Placeholder contract — implemented in later phases."""

    stub: bool = True
    version: str = "0.1.0"
