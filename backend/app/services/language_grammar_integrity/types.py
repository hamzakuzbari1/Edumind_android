"""Wave D integrity contracts."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_grammar_integrity.errors import GrammarIntegrityError
from app.services.language_grammar_integrity.stamp import GrammarStampClaims


@dataclass(frozen=True, slots=True)
class ActivitySessionView:
    activity_session_id: str
    grammar_id: str
    skill: str
    stamp_token: str
    curriculum_version: str
    expires_at: str | None = None


__all__ = [
    "ActivitySessionView",
    "GrammarIntegrityError",
    "GrammarStampClaims",
]
