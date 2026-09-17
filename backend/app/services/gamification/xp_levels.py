"""Level thresholds and progress helpers."""

from __future__ import annotations

LEVEL_THRESHOLDS: tuple[int, ...] = (
    0,
    500,
    1200,
    2200,
    3500,
    5000,
    7000,
    9500,
    12500,
    16000,
)

MAX_LEVEL = len(LEVEL_THRESHOLDS)


def xp_to_level(total_xp: int) -> int:
    level = 1
    for idx, threshold in enumerate(LEVEL_THRESHOLDS):
        if total_xp >= threshold:
            level = idx + 1
    return min(level, MAX_LEVEL)


def level_progress(total_xp: int) -> dict:
    level = xp_to_level(total_xp)
    current_floor = LEVEL_THRESHOLDS[level - 1]
    if level >= MAX_LEVEL:
        return {
            "level": level,
            "total_xp": total_xp,
            "xp_in_level": total_xp - current_floor,
            "xp_for_level": 0,
            "xp_to_next_level": 0,
            "progress_percent": 100,
            "is_max_level": True,
        }
    next_floor = LEVEL_THRESHOLDS[level]
    span = next_floor - current_floor
    xp_in_level = total_xp - current_floor
    xp_to_next = next_floor - total_xp
    percent = round((xp_in_level / span) * 100) if span else 100
    return {
        "level": level,
        "total_xp": total_xp,
        "xp_in_level": xp_in_level,
        "xp_for_level": span,
        "xp_to_next_level": xp_to_next,
        "progress_percent": min(100, max(0, percent)),
        "is_max_level": False,
    }
