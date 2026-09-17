"""Language-module achievement catalog (Phase 7.8)."""

LANGUAGE_ACHIEVEMENT_REGISTRY: dict[str, dict] = {
    "first_conversation": {
        "icon": "💬",
        "title_ar": "أول محادثة",
        "title_en": "First Conversation",
        "description_ar": "أكملت أول محادثة بالإنجليزية مع الذكاء الاصطناعي",
        "category": "speaking",
    },
    "first_speaking_exercise": {
        "icon": "🎤",
        "title_ar": "أول تمرين تحدث",
        "title_en": "First Speaking Exercise",
        "description_ar": "سلّمت أول تمرين تحدث",
        "category": "speaking",
    },
    "first_writing_exercise": {
        "icon": "✍️",
        "title_ar": "أول تمرين كتابة",
        "title_en": "First Writing Exercise",
        "description_ar": "سلّمت أول تمرين كتابة",
        "category": "writing",
    },
    "streak_7": {
        "icon": "🔥",
        "title_ar": "سلسلة 7 أيام",
        "title_en": "7 Day Streak",
        "description_ar": "تعلّمت الإنجليزية 7 أيام متتالية",
        "category": "engagement",
    },
    "streak_30": {
        "icon": "🏅",
        "title_ar": "سلسلة 30 يوماً",
        "title_en": "30 Day Streak",
        "description_ar": "تعلّمت الإنجليزية 30 يوماً متتالياً",
        "category": "engagement",
    },
    "speaking_master": {
        "icon": "🗣️",
        "title_ar": "سيد التحدث",
        "title_en": "Speaking Master",
        "description_ar": "وصلت لنمو ممتاز في مهارة التحدث",
        "category": "mastery",
    },
    "writing_master": {
        "icon": "📝",
        "title_ar": "سيد الكتابة",
        "title_en": "Writing Master",
        "description_ar": "وصلت لنمو ممتاز في مهارة الكتابة",
        "category": "mastery",
    },
    "vocabulary_expert": {
        "icon": "📚",
        "title_ar": "خبير المفردات",
        "title_en": "Vocabulary Expert",
        "description_ar": "تعلّمت عدداً كبيراً من الكلمات",
        "category": "vocabulary",
    },
    "interview_champion": {
        "icon": "💼",
        "title_ar": "بطل المقابلة",
        "title_en": "Interview Champion",
        "description_ar": "أكملت سيناريو مقابلة العمل",
        "category": "scenario",
    },
    "airport_explorer": {
        "icon": "✈️",
        "title_ar": "مستكشف المطار",
        "title_en": "Airport Explorer",
        "description_ar": "أكملت سيناريو المطار",
        "category": "scenario",
    },
    "restaurant_explorer": {
        "icon": "🍽️",
        "title_ar": "مستكشف المطعم",
        "title_en": "Restaurant Explorer",
        "description_ar": "أكملت سيناريو المطعم",
        "category": "scenario",
    },
    "first_promotion": {
        "icon": "⬆️",
        "title_ar": "ترقية المستوى",
        "title_en": "Level Promotion",
        "description_ar": "اجتزت اختبار الترقية وانتقلت إلى المستوى التالي",
        "category": "mastery",
    },
}

SCENARIO_ACHIEVEMENT_MAP = {
    "job_interview": "interview_champion",
    "airport_checkin": "airport_explorer",
    "airport": "airport_explorer",
    "restaurant_order": "restaurant_explorer",
    "restaurant": "restaurant_explorer",
}

SPEAKING_MASTER_GROWTH = 80
WRITING_MASTER_GROWTH = 80
VOCABULARY_EXPERT_KNOWN = 40
VOCABULARY_EXPERT_GROWTH = 70
