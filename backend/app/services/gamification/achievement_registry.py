"""Achievement badge catalog (Phase 8.1 hub)."""

ACHIEVEMENT_REGISTRY: dict[str, dict] = {
    "first_lesson": {
        "icon": "📖",
        "title": "أول درس",
        "description": "أكملت أول درس دراسي",
    },
    "lessons_10": {
        "icon": "📝",
        "title": "10 دروس مكتملة",
        "description": "أكملت 10 دروس دراسية",
    },
    "first_course_completed": {
        "icon": "🎓",
        "title": "أول دورة مكتملة",
        "description": "أكملت أول دورة دراسية بنجاح",
    },
    "streak_30": {
        "icon": "🔥",
        "title": "سلسلة 30 يوماً",
        "description": "درست 30 يوماً متتالياً",
    },
    "lessons_100": {
        "icon": "📚",
        "title": "100 درس مكتمل",
        "description": "أكملت 100 درس دراسي",
    },
    "average_score_95": {
        "icon": "🏆",
        "title": "متوسط 95%",
        "description": "متوسط درجاتك في الاختبارات 95% أو أعلى",
    },
}

LEGACY_KEY_ALIASES: dict[str, str] = {
    "first_perfect_quiz": "average_score_95",
    "streak_7": "streak_30",
    "excellent_quizzes_10": "average_score_95",
}
