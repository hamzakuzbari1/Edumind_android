"""Writing progression state — persisted in LanguageProgression.promotion_readiness_json['writing']."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageSkill
from app.services.language_writing_generation import WRITING_CURRICULUM_KEY, WRITING_GOAL_KEY
from app.services.language_writing_revision.persistence import WRITING_COMPLETION_KEY

WRITING_PROGRESSION_KEY = "writing"
RECENT_NODE_WINDOW = 8


def _content_item_has_student_owner() -> bool:
    return hasattr(LanguageContentItem, "student_id")


def empty_writing_state() -> dict[str, Any]:
    return {
        "completed_node_ids": [],
        "recent_node_ids": [],
        "weak_skills": [],
        "strong_skills": [],
        "grammar_mastery": {},
        "vocabulary_mastery": {},
        "lesson_history": [],
        "coach_memory": {
            "repeated_mistakes": [],
            "repeated_strengths": [],
            "grammar_trends": [],
            "vocabulary_trends": [],
        },
        "lessons_completed_count": 0,
        "current_chain_id": "",
        "current_node_id": "",
        "learning_stage": 1,
        "estimated_lessons_to_next_stage": 5,
        "lessons_today": 0,
        "last_completed_at": None,
    }


def writing_state_from_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    base = empty_writing_state()
    if not isinstance(payload, dict):
        return base
    raw = payload.get(WRITING_PROGRESSION_KEY)
    if not isinstance(raw, dict):
        return base
    merged = dict(base)
    merged.update(raw)
    for key in ("completed_node_ids", "recent_node_ids", "weak_skills", "strong_skills", "lesson_history"):
        if not isinstance(merged.get(key), list):
            merged[key] = []
    for key in ("grammar_mastery", "vocabulary_mastery", "coach_memory"):
        if not isinstance(merged.get(key), dict):
            merged[key] = base[key]
    return merged


def completed_node_ids_from_state(state: dict[str, Any]) -> frozenset[str]:
    return frozenset(str(n) for n in (state.get("completed_node_ids") or []) if n)


async def load_completed_nodes_from_lessons(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> frozenset[str]:
    """Derive completed chain nodes from persisted writing lessons."""
    clauses = [
        LanguageContentItem.language_id == language_id,
        LanguageContentItem.skill == LanguageSkill.writing,
        LanguageContentItem.content_type == "writing_prompt",
    ]
    if _content_item_has_student_owner():
        clauses.append(LanguageContentItem.student_id == student_id)
    result = await db.execute(
        select(LanguageContentItem.body_json).where(*clauses)
    )
    nodes: set[str] = set()
    for (body_json,) in result.all():
        if not isinstance(body_json, dict):
            continue
        if not _content_item_has_student_owner():
            owner = body_json.get("owner_student_id")
            if owner is not None and str(owner) != str(student_id):
                continue
        completion = body_json.get(WRITING_COMPLETION_KEY) or {}
        if isinstance(completion, dict) and completion.get("completed"):
            curriculum = body_json.get(WRITING_CURRICULUM_KEY) or {}
            if isinstance(curriculum, dict):
                nid = curriculum.get("chain_node_id")
                if nid:
                    nodes.add(str(nid))
    return frozenset(nodes)


def merge_completed_nodes(state: dict[str, Any], from_lessons: frozenset[str]) -> dict[str, Any]:
    existing = {str(n) for n in (state.get("completed_node_ids") or []) if n}
    merged = sorted(existing | set(from_lessons))
    out = dict(state)
    out["completed_node_ids"] = merged
    return out
