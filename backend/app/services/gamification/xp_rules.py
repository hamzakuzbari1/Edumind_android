"""Expose XP earning rules from xp_service constants (single source of truth)."""

from __future__ import annotations

from app.services.gamification import xp_service as xp


def get_xp_rules() -> list[dict]:
    return [
        {"category": "lessons", "label": "إكمال درس عادي", "xp": xp.XP_LESSON},
        {"category": "lessons", "label": "إكمال درس طويل (محتوى غني)", "xp": xp.XP_LONG_LESSON},
        {"category": "lessons", "label": f"إكمال وحدة ({xp.MODULE_BATCH_SIZE} دروس)", "xp": xp.XP_MODULE},
        {"category": "lessons", "label": "إكمال دورة كاملة", "xp": xp.XP_COURSE},
        {"category": "quizzes", "label": "تسليم اختبار (أساسي)", "xp": xp.XP_QUIZ_BASE},
        {"category": "quizzes", "label": "مكافأة درجة 80% أو أعلى", "xp": xp.XP_QUIZ_80},
        {"category": "quizzes", "label": "مكافأة درجة 90% أو أعلى", "xp": xp.XP_QUIZ_90},
        {"category": "quizzes", "label": "مكافأة درجة 100%", "xp": xp.XP_QUIZ_100},
        {"category": "planner", "label": "إنجاز مهمة في المخطط الذكي", "xp": xp.XP_PLANNER_TASK},
        {"category": "planner", "label": "إكمال خطة اليوم بالكامل", "xp": xp.XP_PLANNER_DAY},
        {"category": "planner", "label": "إكمال خطة الأسبوع", "xp": xp.XP_PLANNER_WEEK},
        {"category": "streaks", "label": "يوم دراسة مسجّل", "xp": xp.XP_STUDY_DAY},
        {"category": "streaks", "label": "سلسلة 7 أيام", "xp": xp.XP_STREAK_7},
        {"category": "streaks", "label": "سلسلة 14 يوماً", "xp": xp.XP_STREAK_14},
        {"category": "streaks", "label": "سلسلة 30 يوماً", "xp": xp.XP_STREAK_30},
    ]
