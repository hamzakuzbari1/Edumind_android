"""Writing goal resolution (W2) — resolve goal from metadata and aliases."""

from __future__ import annotations

from app.services.language_writing.enums import WritingGoal
from app.services.language_writing_curriculum.goal_profiles import WRITING_GOAL_KEY, profile_for_goal
from app.services.language_writing_curriculum.types import WritingGoalProfile

_GOAL_ALIASES: dict[str, WritingGoal] = {
    "general": WritingGoal.general_english,
    "general_english": WritingGoal.general_english,
    "english": WritingGoal.general_english,
    "travel": WritingGoal.travel,
    "business": WritingGoal.business,
    "ielts": WritingGoal.ielts,
    "academic": WritingGoal.academic,
    "university": WritingGoal.academic,
    "job": WritingGoal.job_interview,
    "job_interview": WritingGoal.job_interview,
    "interview": WritingGoal.job_interview,
    "creative": WritingGoal.creative_writing,
    "creative_writing": WritingGoal.creative_writing,
    "daily": WritingGoal.daily_communication,
    "daily_life": WritingGoal.daily_communication,
    "daily_communication": WritingGoal.daily_communication,
    "communication": WritingGoal.daily_communication,
}


def resolve_writing_goal(raw: str | WritingGoal | None, *, default: WritingGoal = WritingGoal.general_english) -> WritingGoal:
    if raw is None or raw == "":
        return default
    if isinstance(raw, WritingGoal):
        return raw
    key = raw.strip().lower().replace("-", "_").replace(" ", "_")
    return _GOAL_ALIASES.get(key, default)


def resolve_goal_from_metadata(metadata: dict[str, object] | None, *, default: WritingGoal = WritingGoal.general_english) -> WritingGoal:
    if not metadata:
        return default
    raw = metadata.get(WRITING_GOAL_KEY) or metadata.get("learning_goal")
    if isinstance(raw, WritingGoal):
        return raw
    if isinstance(raw, str):
        return resolve_writing_goal(raw, default=default)
    return default


def goal_profile_for_metadata(metadata: dict[str, object] | None) -> WritingGoalProfile:
    return profile_for_goal(resolve_goal_from_metadata(metadata))
