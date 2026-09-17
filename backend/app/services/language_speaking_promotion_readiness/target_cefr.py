"""Deterministic next-CEFR resolution for speaking promotion readiness.

AI must never choose the target CEFR.
"""

from __future__ import annotations

from app.models.language.enums import LanguageLevel
from app.services.language_level_utils import CEFR_RANK, RANK_CEFR
from app.services.language_speaking_learning_stage.curriculum_scope import (
    curriculum_skills_for_official_cefr,
)


class NextCefrResolutionError(ValueError):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


def resolve_next_speaking_cefr(official_cefr: str) -> str:
    """Return next CEFR band or raise NextCefrResolutionError."""
    cefr = (official_cefr or "").upper()
    try:
        level = LanguageLevel(cefr)
    except ValueError as exc:
        raise NextCefrResolutionError("invalid_official_cefr", f"invalid CEFR: {cefr}") from exc

    rank = CEFR_RANK[level]
    if level is LanguageLevel.C2 or rank >= max(CEFR_RANK.values()):
        raise NextCefrResolutionError("terminal_c2", "Already at C2 — no next CEFR")

    nxt = RANK_CEFR[rank + 1]
    target = nxt.value
    nodes = curriculum_skills_for_official_cefr(target)
    if len(nodes) <= 0:
        raise NextCefrResolutionError(
            "target_curriculum_unavailable",
            f"No curriculum skills for target CEFR {target}",
        )
    return target
