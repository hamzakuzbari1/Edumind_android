"""Types for Writing Official Promotion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WritingOfficialPromotionResult:
    success: bool
    old_cefr: str
    new_cefr: str
    reason: str
    session_id: str = ""
