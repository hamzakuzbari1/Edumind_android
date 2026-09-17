"""Derive recent XP activity labels from awarded XP keys."""

from __future__ import annotations

import json

from app.services.gamification import xp_service as xp


def _xp_for_key(key: str) -> tuple[int, str]:
    if key.startswith("lesson:"):
        return xp.XP_LESSON, "إكمال درس"
    if key.startswith("lesson_quiz_bonus:"):
        return xp.XP_QUIZ_100, "مكافأة اختبار درس"
    if key.startswith("lesson_quiz:"):
        return xp.XP_QUIZ_BASE, "اختبار درس"
    if key.startswith("manual_quiz_bonus:"):
        return xp.XP_QUIZ_100, "مكافأة اختبار"
    if key.startswith("manual_quiz:"):
        return xp.XP_QUIZ_BASE, "اختبار يدوي"
    if key.startswith("module:"):
        return xp.XP_MODULE, "إكمال وحدة دراسية"
    if key.startswith("course:"):
        return xp.XP_COURSE, "إكمال دورة"
    if key.startswith("planner_task:"):
        return xp.XP_PLANNER_TASK, "مهمة مخطط ذكي"
    if key.startswith("planner_day:"):
        return xp.XP_PLANNER_DAY, "خطة يوم كاملة"
    if key.startswith("planner_week:"):
        return xp.XP_PLANNER_WEEK, "خطة أسبوع كاملة"
    if key.startswith("study_day:"):
        return xp.XP_STUDY_DAY, "يوم دراسة"
    if key == "streak_milestone:7":
        return xp.XP_STREAK_7, "سلسلة 7 أيام"
    if key == "streak_milestone:14":
        return xp.XP_STREAK_14, "سلسلة 14 يوماً"
    if key == "streak_milestone:30":
        return xp.XP_STREAK_30, "سلسلة 30 يوماً"
    return 0, "نشاط XP"


def parse_awarded_keys(raw: str | None) -> set[str]:
    try:
        data = json.loads(raw or "[]")
    except Exception:
        return set()
    if not data:
        return set()
    if isinstance(data[0], dict):
        return {str(item.get("key", "")) for item in data if item.get("key")}
    return {str(k) for k in data}


def build_recent_xp_activity(
    awarded_keys_raw: str | None,
    achievements: list[dict],
    *,
    limit: int = 12,
) -> list[dict]:
    items: list[dict] = []

    for ach in achievements:
        items.append(
            {
                "label": f"إنجاز: {ach.get('title', '')}",
                "xp": 0,
                "occurred_at": ach.get("unlocked_at"),
                "kind": "achievement",
            }
        )

    keys = sorted(parse_awarded_keys(awarded_keys_raw), reverse=True)
    for key in keys:
        amount, label = _xp_for_key(key)
        if amount <= 0:
            continue
        items.append(
            {
                "label": label,
                "xp": amount,
                "occurred_at": None,
                "kind": "xp",
            }
        )

    with_dates = [i for i in items if i.get("occurred_at")]
    without_dates = [i for i in items if not i.get("occurred_at")]
    with_dates.sort(key=lambda i: str(i.get("occurred_at") or ""), reverse=True)
    merged = with_dates + without_dates
    return merged[:limit]
