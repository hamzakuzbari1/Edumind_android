"""Graceful degradation when gamification migrations are not yet applied."""

from __future__ import annotations

import logging

from sqlalchemy.exc import DBAPIError, ProgrammingError

from app.services.gamification.achievement_registry import ACHIEVEMENT_REGISTRY
from app.services.gamification.xp_levels import level_progress
from app.services.gamification.xp_rules import get_xp_rules

logger = logging.getLogger(__name__)

_GAMIFICATION_TABLES = ("student_xp", "student_achievements")


def is_missing_gamification_table(exc: BaseException) -> bool:
    orig = getattr(exc, "orig", exc)
    msg = str(orig).lower()
    if "does not exist" not in msg and "undefinedtable" not in msg:
        return False
    return any(table in msg for table in _GAMIFICATION_TABLES)


def empty_gamification_profile(*, current_streak: int = 0, longest_streak: int = 0) -> dict:
    progress = level_progress(0)
    streak = max(0, current_streak)
    return {
        "level": progress["level"],
        "total_xp": progress["total_xp"],
        "xp_to_next_level": progress["xp_to_next_level"],
        "xp_in_level": progress["xp_in_level"],
        "xp_for_level": progress["xp_for_level"],
        "progress_percent": progress["progress_percent"],
        "is_max_level": progress["is_max_level"],
        "current_streak": streak,
        "longest_streak": max(0, longest_streak),
        "achievements": [],
        "achievement_count": 0,
        "streak_display": f"🔥 {streak} يوم" if streak else "🔥 0 يوم",
        "badges": [
            {
                "achievement_key": key,
                "icon": meta["icon"],
                "title": meta["title"],
                "description": meta["description"],
                "unlocked": False,
                "unlocked_at": None,
            }
            for key, meta in ACHIEVEMENT_REGISTRY.items()
        ],
        "xp_rules": get_xp_rules(),
        "recent_activity": [],
    }


def log_missing_tables(action: str) -> None:
    logger.warning("Gamification tables missing — %s skipped (run alembic upgrade head)", action)
