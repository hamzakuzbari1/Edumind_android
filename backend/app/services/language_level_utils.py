"""CEFR helpers — bottleneck for internal path logic; dashboards show all four skills."""

from __future__ import annotations

from app.models.language.enums import LanguageLevel, LanguageSkill

CEFR_RANK: dict[LanguageLevel, int] = {
    LanguageLevel.A1: 1,
    LanguageLevel.A2: 2,
    LanguageLevel.B1: 3,
    LanguageLevel.B2: 4,
    LanguageLevel.C1: 5,
    LanguageLevel.C2: 6,
}

RANK_CEFR: dict[int, LanguageLevel] = {v: k for k, v in CEFR_RANK.items()}

SKILL_LABELS_AR: dict[str, str] = {
    LanguageSkill.reading.value: "Reading",
    LanguageSkill.listening.value: "Listening",
    LanguageSkill.writing.value: "Writing",
    LanguageSkill.speaking.value: "Speaking",
}


def bottleneck_level(levels: dict[str, LanguageLevel | str | None]) -> LanguageLevel | None:
    """Lowest CEFR across skills — for path generation and internal analytics only."""
    ranks: list[int] = []
    for key in ("reading", "listening", "writing", "speaking"):
        lv = levels.get(key)
        if lv is None:
            continue
        if isinstance(lv, str):
            try:
                lv = LanguageLevel(lv)
            except ValueError:
                continue
        ranks.append(CEFR_RANK[lv])
    if not ranks:
        return None
    return RANK_CEFR[min(ranks)]


CERTIFICATE_LEVELS: tuple[LanguageLevel, ...] = (
    LanguageLevel.A1,
    LanguageLevel.A2,
    LanguageLevel.B1,
)


def meets_certificate_threshold(
    levels: dict[str, LanguageLevel | str | None],
    required: LanguageLevel,
) -> bool:
    """True when reading, listening, writing, and speaking are all >= required CEFR."""
    req_rank = CEFR_RANK[required]
    for key in ("reading", "listening", "writing", "speaking"):
        lv = levels.get(key)
        if lv is None:
            return False
        if isinstance(lv, str):
            try:
                lv = LanguageLevel(lv)
            except ValueError:
                return False
        if CEFR_RANK[lv] < req_rank:
            return False
    return True


def primary_focus_and_strength(
    levels: dict[str, LanguageLevel | str | None],
) -> tuple[str | None, str | None]:
    """Weakest skill = primary focus; strongest = strength area."""
    parsed: dict[str, int] = {}
    for key in ("reading", "listening", "writing", "speaking"):
        lv = levels.get(key)
        if lv is None:
            continue
        if isinstance(lv, str):
            try:
                lv = LanguageLevel(lv)
            except ValueError:
                continue
        parsed[key] = CEFR_RANK[lv]
    if not parsed:
        return None, None
    focus = min(parsed, key=lambda k: parsed[k])
    strength = max(parsed, key=lambda k: parsed[k])
    return focus, strength
