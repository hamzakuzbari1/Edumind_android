"""Curriculum history extraction (Phase 2.3)."""

from __future__ import annotations

from app.services.language_listening_curriculum.types import CurriculumHistoryEntry
from app.services.language_listening_intelligence.memory import HISTORY_KEY as INTELLIGENCE_KEY

CURRICULUM_KEY = "listening_curriculum"


def curriculum_entry_from_metadata(
    intelligence: dict | None,
    curriculum: dict | None,
    *,
    generation_index: int = 0,
) -> CurriculumHistoryEntry | None:
    if not isinstance(intelligence, dict):
        return None
    situation = str(intelligence.get("situation") or "").strip()
    if not situation:
        return None
    curriculum = curriculum if isinstance(curriculum, dict) else {}
    skills = curriculum.get("skill_focus") or []
    objectives = curriculum.get("objectives") or []
    return CurriculumHistoryEntry(
        situation=situation,
        category=str(intelligence.get("category") or ""),
        narrative_format=str(intelligence.get("narrative_format") or ""),
        skill_focus=tuple(str(s) for s in skills if s),
        objectives=tuple(str(o) for o in objectives if o),
        knowledge_node=str(curriculum.get("knowledge_node") or situation),
        level=str(intelligence.get("level") or ""),
        generation_index=generation_index,
        lesson_intent=str(curriculum.get("lesson_intent") or "balanced_coverage"),
    )


def extract_curriculum_history(bodies: list[dict]) -> list[CurriculumHistoryEntry]:
    entries: list[CurriculumHistoryEntry] = []
    for idx, body in enumerate(bodies):
        if not isinstance(body, dict):
            continue
        entry = curriculum_entry_from_metadata(
            body.get(INTELLIGENCE_KEY),
            body.get(CURRICULUM_KEY),
            generation_index=idx,
        )
        if entry:
            entries.append(entry)
    return entries


def recent_skill_focus(history: list[CurriculumHistoryEntry], window: int = 15) -> list[str]:
    skills: list[str] = []
    for entry in history[-window:]:
        if entry.skill_focus:
            skills.append(entry.skill_focus[0])
    return skills


def seen_knowledge_nodes(history: list[CurriculumHistoryEntry]) -> set[str]:
    return {entry.knowledge_node for entry in history if entry.knowledge_node}
