"""Rule-based Arabic schedule/event extraction from natural language."""

import json
import re
from datetime import datetime, timedelta, timezone

from app.models.planner import LifeEventType

SUBJECTS = [
    "رياضيات",
    "كيمياء",
    "فيزياء",
    "أحياء",
    "عربي",
    "انجليزي",
    "إنجليزي",
    "تاريخ",
    "جغرافيا",
    "علوم",
]

DAY_MAP = {
    "السبت": 5,
    "الأحد": 6,
    "الاحد": 6,
    "الاثنين": 0,
    "الإثنين": 0,
    "الثلاثاء": 1,
    "الأربعاء": 2,
    "الاربعاء": 2,
    "الخميس": 3,
    "الجمعة": 4,
}

PERIOD_MAP = {
    "ليل": "night",
    "بالليل": "night",
    "مساء": "evening",
    "مساءً": "evening",
    "صبح": "morning",
    "صباح": "morning",
    "الصبح": "morning",
    "الصباح": "morning",
}


def _detect_subject(text: str) -> str | None:
    for subj in SUBJECTS:
        if subj in text:
            return subj
    return None


def _detect_day(text: str) -> int | None:
    for name, idx in DAY_MAP.items():
        if name in text:
            return idx
    return None


def _detect_time(text: str) -> str | None:
    m = re.search(r"(\d{1,2})\s*(?::\d{2})?\s*(?:مساء|صباح|مساءً|pm|am)?", text)
    if m:
        hour = int(m.group(1))
        if "مساء" in text or "pm" in text.lower():
            if hour < 12:
                hour += 12
        return f"{hour:02d}:00"
    m = re.search(r"(\d{1,2}):(\d{2})", text)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    return None


def _days_until_exam(text: str) -> int | None:
    m = re.search(r"بعد\s+(\d+)\s+(?:يوم|أيام)", text)
    if m:
        return int(m.group(1))
    return None


def extract_from_message(message: str) -> dict:
    """Deterministic extraction — LLM augmentation can wrap this later."""
    text = message.strip()
    lower = text.lower()
    result: dict = {
        "life_events": [],
        "profile_updates": {},
        "weak_subjects": [],
        "notes": [text[:200]],
    }

    subject = _detect_subject(text)
    day = _detect_day(text)
    start_time = _detect_time(text)

    for key, period in PERIOD_MAP.items():
        if key in text:
            result["profile_updates"]["preferred_period"] = period
            break

    if any(w in text for w in ("ضعيف", "ضعيفة", "صعب", "صعبة", "ما بفهم")):
        if subject:
            result["weak_subjects"].append(subject)
        elif "رياضيات" in text:
            result["weak_subjects"].append("رياضيات")

    if any(w in text for w in ("دوام", "مدرسة", "مدرسة الصبح", "مدرسة الصباح")):
        result["profile_updates"]["school_start"] = "08:00"
        result["profile_updates"]["school_end"] = "14:00"
        result["life_events"].append(
            {
                "title": "دوام مدرسة",
                "event_type": LifeEventType.school.value,
                "day_of_week": None,
                "start_time": "08:00",
                "duration_minutes": 360,
                "is_blocking": True,
            }
        )

    if any(w in text for w in ("درس خصوصي", "درس خصوص", "حصة خصوصية")):
        result["life_events"].append(
            {
                "title": f"درس خصوصي {subject or ''}".strip(),
                "event_type": LifeEventType.private_lesson.value,
                "day_of_week": day,
                "start_time": start_time or "18:00",
                "duration_minutes": 90,
                "is_blocking": True,
                "subject": subject,
            }
        )

    if "مباراة" in text or "تمرين" in text or "رياضة" in text:
        result["life_events"].append(
            {
                "title": "مباراة / نشاط رياضي",
                "event_type": LifeEventType.sport.value,
                "day_of_week": day or 4,
                "start_time": start_time or "16:00",
                "duration_minutes": 120,
                "is_blocking": True,
            }
        )

    if any(w in text for w in ("مناسبة عائلية", "عائلة", "عزيمة", "زيارة")):
        result["life_events"].append(
            {
                "title": "مناسبة عائلية",
                "event_type": LifeEventType.family.value,
                "day_of_week": day or 3,
                "start_time": start_time or "17:00",
                "duration_minutes": 180,
                "is_blocking": True,
            }
        )

    if "امتحان" in text or "اختبار" in text:
        days = _days_until_exam(text)
        event_date = None
        if days is not None:
            event_date = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        result["life_events"].append(
            {
                "title": f"امتحان {subject or ''}".strip(),
                "event_type": LifeEventType.exam.value,
                "day_of_week": day,
                "event_date": event_date,
                "start_time": "09:00",
                "duration_minutes": 120,
                "is_blocking": True,
                "subject": subject,
            }
        )
        if subject:
            result["weak_subjects"].append(subject)

    if not result["life_events"] and not result["profile_updates"] and not result["weak_subjects"]:
        result["notes"] = [text[:200]]

    return result


async def try_llm_augment(message: str, base: dict) -> dict:
    """Optional LLM layer — falls back to rule-based extraction."""
    try:
        from app.services.ai_service import generate_planner_interpretation

        llm_data = await generate_planner_interpretation(message)
        if llm_data:
            for ev in llm_data.get("life_events", []):
                if ev not in base["life_events"]:
                    base["life_events"].append(ev)
            base["profile_updates"].update(llm_data.get("profile_updates", {}))
            for s in llm_data.get("weak_subjects", []):
                if s not in base["weak_subjects"]:
                    base["weak_subjects"].append(s)
    except Exception:
        pass
    return base
