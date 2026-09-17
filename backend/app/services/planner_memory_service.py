"""Planner profile and memory persistence."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planner import PlannerProfile


async def get_or_create_profile(db: AsyncSession, student_id: int) -> PlannerProfile:
    result = await db.execute(select(PlannerProfile).where(PlannerProfile.student_id == student_id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = PlannerProfile(student_id=student_id)
        db.add(profile)
        await db.flush()
    return profile


def profile_to_dict(profile: PlannerProfile) -> dict:
    weak = []
    memory = {}
    try:
        weak = json.loads(profile.weak_subjects_json or "[]")
    except Exception:
        weak = []
    try:
        memory = json.loads(profile.memory_json or "{}")
    except Exception:
        memory = {}
    return {
        "preferred_period": profile.preferred_period,
        "school_start": profile.school_start,
        "school_end": profile.school_end,
        "max_daily_minutes": profile.max_daily_minutes,
        "weak_subjects": weak if isinstance(weak, list) else [],
        "memory": memory if isinstance(memory, dict) else {},
    }


async def update_profile_from_extraction(
    db: AsyncSession,
    profile: PlannerProfile,
    extracted: dict,
) -> PlannerProfile:
    if extracted.get("preferred_period") and extracted["preferred_period"] in ("morning", "evening", "night"):
        profile.preferred_period = extracted["preferred_period"]
    if extracted.get("school_start"):
        profile.school_start = extracted["school_start"]
    if extracted.get("school_end"):
        profile.school_end = extracted["school_end"]
    if extracted.get("max_daily_minutes"):
        profile.max_daily_minutes = extracted["max_daily_minutes"]

    weak = json.loads(profile.weak_subjects_json or "[]")
    if not isinstance(weak, list):
        weak = []
    for subj in extracted.get("weak_subjects", []):
        if subj and subj not in weak:
            weak.append(subj)
    profile.weak_subjects_json = json.dumps(weak, ensure_ascii=False)

    memory = json.loads(profile.memory_json or "{}")
    if not isinstance(memory, dict):
        memory = {}
    notes = extracted.get("notes", [])
    if notes:
        memory.setdefault("notes", [])
        memory["notes"].extend(notes)
        memory["notes"] = memory["notes"][-20:]
    profile.memory_json = json.dumps(memory, ensure_ascii=False)
    await db.flush()
    return profile
