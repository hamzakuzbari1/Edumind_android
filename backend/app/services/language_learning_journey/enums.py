"""Learning Journey UI status enums — compose-only; no unlock logic."""

from __future__ import annotations

from enum import StrEnum


class JourneyStageStatus(StrEnum):
    completed = "completed"
    current = "current"
    unlocked = "unlocked"
    locked = "locked"


class JourneyLevelStatus(StrEnum):
    done = "done"
    current = "current"
    locked = "locked"
