"""Expanded listening objective catalog (Phase 2.3.1)."""

from __future__ import annotations

from app.services.language_cefr.engine import normalize_cefr_level

# (objective_id, label, related_skills, min_level)
CATALOG: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    ("main_idea", "Identify the main idea of a passage", ("main_idea",), "A1"),
    ("detail", "Catch explicit factual details", ("detail",), "A1"),
    ("sequence", "Follow the order of events or steps", ("sequence",), "A1"),
    ("purpose", "Understand why a speaker is talking", ("purpose",), "A1"),
    ("numbers", "Understand numbers, prices, and quantities", ("detail",), "A1"),
    ("dates", "Understand dates and times", ("detail", "sequence"), "A1"),
    ("directions", "Follow directions and locations", ("detail", "sequence"), "A1"),
    ("announcements", "Understand public announcements", ("purpose", "detail"), "A1"),
    ("instructions", "Follow spoken instructions", ("detail", "sequence"), "A2"),
    ("inference", "Make a logical inference from what is said", ("inference",), "B1"),
    ("speaker_intention", "Recognize why a speaker says something", ("speaker_intention",), "B1"),
    ("tone", "Identify speaker tone or attitude", ("tone",), "B1"),
    ("prediction", "Predict what comes next", ("prediction",), "B1"),
    ("opinion", "Identify a stated opinion", ("opinion",), "B1"),
    ("agreement", "Notice agreement between speakers", ("opinion", "speaker_intention"), "B1"),
    ("disagreement", "Notice disagreement or contrast", ("opinion", "tone"), "B1"),
    ("cause_effect", "Link causes and results in speech", ("inference", "sequence"), "B1"),
    ("comparisons", "Compare two options or views", ("inference", "main_idea"), "B1"),
    ("problems_solutions", "Follow a problem and its resolution", ("inference", "sequence"), "B1"),
    ("evidence", "Connect a claim to supporting evidence", ("detail", "inference"), "B2"),
    ("examples", "Recognize examples that illustrate a point", ("detail", "main_idea"), "B2"),
    ("transitions", "Follow discourse markers and transitions", ("sequence", "purpose"), "B2"),
    ("conclusions", "Understand how a speaker concludes", ("main_idea", "purpose"), "B2"),
    ("attitude", "Interpret speaker attitude or stance", ("tone", "speaker_intention"), "B2"),
    ("fact_vs_opinion", "Distinguish fact from opinion", ("opinion", "detail"), "B2"),
    ("bias", "Detect bias or slant in speech", ("bias", "tone"), "C1"),
)

_LEVEL_RANK = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}


def catalog_for_level(level: str) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """Return objectives available at ``level`` (includes lower-level objectives)."""
    norm = normalize_cefr_level(level)
    rank = _LEVEL_RANK.get(norm, 3)
    out: list[tuple[str, str, tuple[str, ...]]] = []
    seen: set[str] = set()
    for oid, label, skills, min_level in CATALOG:
        if _LEVEL_RANK.get(min_level, 99) <= rank and oid not in seen:
            seen.add(oid)
            out.append((oid, label, skills))
    return tuple(out)


def objective_skills(objective_id: str) -> tuple[str, ...]:
    for oid, _, skills, _ in CATALOG:
        if oid == objective_id:
            return skills
    return ("detail",)
