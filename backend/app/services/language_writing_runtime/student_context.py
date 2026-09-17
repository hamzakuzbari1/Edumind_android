"""Student context helpers for writing runtime (W6) — read official level only."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.enums import LanguageSkill
from app.services.language_writing.enums import OfficialWritingCEFR
from app.services.language_progression_service import get_official_cefr
from app.services.language_writing_curriculum.goal_resolver import resolve_writing_goal, resolve_goal_from_metadata
from app.services.language_writing.enums import WritingGoal


async def official_writing_cefr_for_student(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    default: OfficialWritingCEFR = OfficialWritingCEFR.B1,
) -> OfficialWritingCEFR:
    try:
        read = await get_official_cefr(
            db,
            student_id=student_id,
            language_id=language_id,
            skill=LanguageSkill.writing,
        )
        return OfficialWritingCEFR(read.level.value)
    except ValueError:
        return default


def writing_goal_from_preferences(preferences: dict[str, object] | None) -> WritingGoal:
    if not preferences:
        return WritingGoal.general_english
    resolved = resolve_goal_from_metadata(preferences)
    if resolved != WritingGoal.general_english:
        return resolved
    memory = preferences.get("learner_memory")
    if not isinstance(memory, dict):
        memory = preferences.get("memory")
    if isinstance(memory, dict):
        resolved = resolve_goal_from_metadata(memory)
        if resolved != WritingGoal.general_english:
            return resolved
        goals = memory.get("learning_goals")
    else:
        goals = preferences.get("learning_goals")
    if isinstance(goals, list):
        for raw in goals:
            resolved = resolve_writing_goal(str(raw), default=WritingGoal.general_english)
            if resolved != WritingGoal.general_english:
                return resolved
    future_goal = (memory if isinstance(memory, dict) else preferences).get("future_goal")
    if isinstance(future_goal, str):
        return resolve_writing_goal(future_goal, default=WritingGoal.general_english)
    return WritingGoal.general_english
