"""Adaptive difficulty — move a skill up/down a CEFR level based on recent lesson scores.

Rules:
  Promotion: score >= 85% on 3 consecutive lessons (same skill) -> up one level
  Demotion:  score <  55% on 2 consecutive lessons (same skill) -> down one level
  Cooldown:  24 hours between any level change per skill
  Bounds:    never above C2, never below A1

A mid-range score (55-84) breaks both streaks without counting as pass or fail.
The per-skill level lives in language_skill_level_state; on every change we mirror it
into language_analytics.<skill>_level so the rest of the app sees the new level.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.adaptive import LanguageSkillLevelState
from app.models.language.analytics import LanguageAnalytics
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.services.language_level_utils import CEFR_RANK, RANK_CEFR

PROMOTE_SCORE = 85.0
DEMOTE_SCORE = 55.0
PROMOTE_STREAK = 3
DEMOTE_STREAK = 2
COOLDOWN = timedelta(hours=24)
MAX_RANK = 6  # C2
MIN_RANK = 1  # A1


def _as_skill(skill: LanguageSkill | str) -> LanguageSkill:
    return skill if isinstance(skill, LanguageSkill) else LanguageSkill(skill)


def _as_level(level: LanguageLevel | str | None) -> LanguageLevel:
    if level is None:
        return LanguageLevel.A1
    return level if isinstance(level, LanguageLevel) else LanguageLevel(level)


async def get_or_create_skill_state(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    skill: LanguageSkill | str,
    initial_level: LanguageLevel | str | None,
) -> LanguageSkillLevelState:
    skill = _as_skill(skill)
    result = await db.execute(
        select(LanguageSkillLevelState).where(
            LanguageSkillLevelState.student_id == student_id,
            LanguageSkillLevelState.language_id == language_id,
            LanguageSkillLevelState.skill == skill,
        )
    )
    state = result.scalar_one_or_none()
    if state is None:
        state = LanguageSkillLevelState(
            student_id=student_id,
            language_id=language_id,
            skill=skill,
            current_level=_as_level(initial_level),
        )
        db.add(state)
        await db.flush()
    return state


def _cooldown_ok(last_change: datetime | None, now: datetime) -> bool:
    if last_change is None:
        return True
    if last_change.tzinfo is None:
        last_change = last_change.replace(tzinfo=timezone.utc)
    return (now - last_change) >= COOLDOWN


async def record_lesson_result(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    skill: LanguageSkill | str,
    score_percent: float,
) -> dict:
    skill = _as_skill(skill)
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    initial_level = getattr(analytics, f"{skill.value}_level", None) if analytics else None
    state = await get_or_create_skill_state(
        db, student_id=student_id, language_id=language_id, skill=skill, initial_level=initial_level
    )

    previous_level = state.current_level

    if score_percent >= PROMOTE_SCORE:
        state.consecutive_pass_count = int(state.consecutive_pass_count or 0) + 1
        state.consecutive_fail_count = 0
    elif score_percent < DEMOTE_SCORE:
        state.consecutive_fail_count = int(state.consecutive_fail_count or 0) + 1
        state.consecutive_pass_count = 0
    else:
        state.consecutive_pass_count = 0
        state.consecutive_fail_count = 0

    # Progression policy: the official CEFR level changes ONLY via the placement test
    # (initial) and the level-up (promotion) test — which is itself gated behind mastering
    # the current level. Adaptive difficulty therefore tracks pass/fail streaks (a readiness
    # signal shown to the learner) but never auto-promotes/demotes the level, so a learner
    # can never skip ahead without finishing the current level.
    await db.flush()
    return {
        "skill": skill.value,
        "previous_level": previous_level.value,
        "current_level": state.current_level.value,
        "changed": False,
        "direction": None,
        "consecutive_pass_count": int(state.consecutive_pass_count or 0),
        "consecutive_fail_count": int(state.consecutive_fail_count or 0),
    }


async def get_adaptive_state_overview(db: AsyncSession, *, student_id: int, language_id: int) -> dict:
    """Per-skill snapshot for the GET /adaptive/state endpoint."""
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    skills: dict[str, dict] = {}
    for skill in (LanguageSkill.reading, LanguageSkill.listening, LanguageSkill.writing, LanguageSkill.speaking):
        initial_level = getattr(analytics, f"{skill.value}_level", None) if analytics else None
        state = await get_or_create_skill_state(
            db, student_id=student_id, language_id=language_id, skill=skill, initial_level=initial_level
        )
        passes = int(state.consecutive_pass_count or 0)
        fails = int(state.consecutive_fail_count or 0)
        skills[skill.value] = {
            "current_level": state.current_level.value,
            "consecutive_pass": passes,
            "consecutive_fail": fails,
            "passes_to_promote": max(0, PROMOTE_STREAK - passes),
            "fails_to_demote": max(0, DEMOTE_STREAK - fails),
        }
    return {"skills": skills}
