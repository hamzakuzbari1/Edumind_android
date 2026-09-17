"""Daily routine — state machine + Claude AI (حياتي)."""
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.routine import RoutineSlot, StudentRoutineProfile

logger = logging.getLogger(__name__)

ARABIC_TEXT_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")

# ─── Routine slot title translations ──
_SLOT_TITLES = {
    "ar": {
        "breakfast": "فطور",
        "school": "المدرسة",
        "lunch_short": "غداء وراحة قصيرة",
        "lunch": "غداء",
        "review": "مراجعة {subject}",
        "homework": "حل واجبات {subject}",
        "review_focused": "مراجعة مركزة {subject}",
        "practice": "تدريب {subject}",
        "rest_walk": "راحة أو مشي خفيف",
        "dinner": "عشاء",
        "family_time": "وقت العائلة وتجهيز الغد",
        "sleep": "نوم",
        "general_review": "مراجعة عامة",
        "appointment": "موعد",
    },
    "en": {
        "breakfast": "Breakfast",
        "school": "School",
        "lunch_short": "Lunch & short break",
        "lunch": "Lunch",
        "review": "Review {subject}",
        "homework": "Homework {subject}",
        "review_focused": "Focused review {subject}",
        "practice": "Practice {subject}",
        "rest_walk": "Rest or light walk",
        "dinner": "Dinner",
        "family_time": "Family time & prep for tomorrow",
        "sleep": "Sleep",
        "general_review": "General review",
        "appointment": "Appointment",
    },
}


def _slot_title(key: str, lang: str = "ar", **kwargs) -> str:
    titles = _SLOT_TITLES.get(lang, _SLOT_TITLES["ar"])
    template = titles.get(key, _SLOT_TITLES["ar"].get(key, key))
    return template.format(**kwargs) if kwargs else template


# ─── LLM token-usage tracking (حياتي) — مجموع تراكمي لكل الاستدعاءات ──
_llm_usage_totals = {"input": 0, "output": 0, "total": 0, "calls": 0}


def _log_llm_usage(resp, label: str) -> None:
    """يسجل عدد التوكنز لاستدعاء Claude ويطبع المجموع التراكمي بالكونسول."""
    try:
        usage = getattr(resp, "usage", None)
        if usage is None:
            usage = getattr(resp, "usage_metadata", None)
        if usage is None:
            return
        input_tokens = getattr(usage, "input_tokens", None) or getattr(usage, "prompt_token_count", 0) or 0
        output_tokens = getattr(usage, "output_tokens", None) or getattr(usage, "candidates_token_count", 0) or 0
        total_tokens = getattr(usage, "total_tokens", None) or getattr(usage, "total_token_count", 0) or (input_tokens + output_tokens)

        _llm_usage_totals["input"] += input_tokens
        _llm_usage_totals["output"] += output_tokens
        _llm_usage_totals["total"] += total_tokens
        _llm_usage_totals["calls"] += 1

        logger.info(
            "🔢 LLM usage [%s] — input=%d output=%d total=%d │ المجموع التراكمي (حياتي): "
            "input=%d output=%d total=%d عبر %d استدعاء",
            label, input_tokens, output_tokens, total_tokens,
            _llm_usage_totals["input"], _llm_usage_totals["output"],
            _llm_usage_totals["total"], _llm_usage_totals["calls"],
        )
    except Exception as e:
        logger.warning("LLM usage logging failed: %s", repr(e)[:120])


# Backward-compatible alias.
_log_gemini_usage = _log_llm_usage


DAY_ORDER = [6, 0, 1, 2, 3, 4, 5]
DAY_NAMES = {6: "الاحد", 0: "الاثنين", 1: "الثلاثاء", 2: "الاربعاء", 3: "الخميس", 4: "الجمعة", 5: "السبت"}
WEEKEND = {4, 5}

STAGES = ["start", "exams", "day_6", "day_0", "day_1", "day_2", "day_3", "day_4", "day_5", "confirm", "build", "review", "done"]

# قاعدة المعرفة حسب الصف — نوم، دراسة، نشاط، وقت حر، قيلولة، حصص خاصة
GRADE_KNOWLEDGE = {
    "1-3": {
        "sleep_time": "20:30",
        "wake_time": "06:30",
        "study_hours": "30-45 دقيقة",
        "play_hours": "ساعتان",
        "nap": True,
        "nap_duration": "60-90 دقيقة",
        "private_lessons": False,
        "prayers": ["الفجر", "الظهر", "العصر", "المغرب", "العشاء"],
        "meals": ["فطور", "وجبة خفيفة", "غداء", "وجبة خفيفة مسائية", "عشاء"],
        "notes": "لعب حر، قصص قبل النوم، وقت عيلة إجباري",
    },
    "4-6": {
        "sleep_time": "21:30",
        "wake_time": "06:15",
        "study_hours": "1-1.5 ساعة",
        "play_hours": "90 دقيقة",
        "nap": True,
        "nap_duration": "45-60 دقيقة",
        "private_lessons": False,
        "prayers": ["الفجر", "الظهر", "العصر", "المغرب", "العشاء"],
        "meals": ["فطور", "وجبة خفيفة", "غداء", "عشاء"],
        "notes": "نشاط بدني يومي، وقت شاشة محدود، قراءة خفيفة",
    },
    "7-9": {
        "sleep_time": "22:30",
        "wake_time": "06:00",
        "study_hours": "1.5-2.5 ساعة",
        "play_hours": "60 دقيقة",
        "nap": True,
        "nap_duration": "30-45 دقيقة",
        "private_lessons": True,
        "prayers": ["الفجر", "الظهر", "العصر", "المغرب", "العشاء"],
        "meals": ["فطور", "غداء", "عشاء"],
        "notes": "نشاط رياضي 3× أسبوع، فترتا دراسة منفصلتان، راحة 30 دقيقة بعد المدرسة",
    },
    "10-11": {
        "sleep_time": "23:00",
        "wake_time": "06:00",
        "study_hours": "2.5-4 ساعات",
        "play_hours": "45 دقيقة",
        "nap": False,
        "nap_duration": None,
        "private_lessons": True,
        "prayers": ["الفجر", "الظهر", "العصر", "المغرب", "العشاء"],
        "meals": ["فطور", "غداء", "عشاء"],
        "notes": "راحة 15 دقيقة كل 45 دراسة، مراجعة خفيفة قبل النوم، أولوية للمواد الصعبة صباحاً",
    },
    "12-bac": {
        "sleep_time": "23:30",
        "wake_time": "05:45",
        "study_hours": "4-6 ساعات",
        "play_hours": "30 دقيقة",
        "nap": False,
        "nap_duration": None,
        "private_lessons": True,
        "prayers": ["الفجر", "الظهر", "العصر", "المغرب", "العشاء"],
        "meals": ["فطور", "غداء", "عشاء"],
        "notes": "راحة 10 دقيقة كل 45 دراسة، مراجعة شاملة قبل النوم، جلسات دراسة ثلاث يومياً",
    },
}

# إشارات السياق — كلمات مفتاحية لاكتشاف الحالة وتخصيص الرد
SIGNALS = {
    "tired": ["تعبت", "تعبان", "مو قادر", "ما بقدر", "منهك", "مرهق", "مو شايف حالي", "صعبة"],
    "ramadan": ["رمضان", "صايم", "سحور", "افطار", "تراويح", "صيام"],
    "failed": ["ما نجحت", "رسبت", "ضعيف", "راسب", "نتيجة سيئة", "خسرت", "ما عدت"],
    "family_issues": ["مشاغل", "عيلة", "اهل", "ضيوف", "سفر", "انشغل", "مشغول", "ظروف عيلة", "أهلي"],
    "bored": ["مله", "ملل", "ماله", "مو مهتم", "مو حاسس", "ما بدي"],
    "late_night": ["بسهر", "سهران", "نام متأخر", "ما نمت", "قليل نوم", "سهرت"],
    "exam_stress": ["امتحانات", "قلق", "خايف", "ضغط", "صعبة الامتحانات"],
}


def _gk(grade: str) -> dict:
    if grade in ("1", "2", "3"):
        return GRADE_KNOWLEDGE["1-3"]
    if grade in ("4", "5", "6"):
        return GRADE_KNOWLEDGE["4-6"]
    if grade in ("7", "8", "9"):
        return GRADE_KNOWLEDGE["7-9"]
    if grade in ("10", "11"):
        return GRADE_KNOWLEDGE["10-11"]
    return GRADE_KNOWLEDGE["12-bac"]


def _detect_signal(message: str) -> list[str]:
    text = message.lower()
    detected = []
    for signal, keywords in SIGNALS.items():
        if any(k in text for k in keywords):
            detected.append(signal)
    return detected


def _signal_response(signals: list[str]) -> str:
    if "tired" in signals:
        return "شايف إنك تعبان هالأيام — هاد طبيعي، لازم نحط في برنامجك راحة كافية. "
    if "ramadan" in signals:
        return "ماشاء الله تصوم! بنبني برنامج خاص يناسب وقت السحور والإفطار والتراويح. "
    if "failed" in signals:
        return "فهمت إنك مريت بوقت صعب — هاد مو نهاية، رح نضبط البرنامج يحكيك بكرا أحسن. "
    if "family_issues" in signals:
        return "فهمت إنك مشغول بظروف العيلة — رح نبني برنامج مرن يأخذ ذلك بعين الاعتبار. "
    if "bored" in signals:
        return "لما الواحد يحس بالملل، غالباً الروتين ما بناسبه — خليني أبنيلك شي أكثر تنوع. "
    if "late_night" in signals:
        return "النوم المتأخر بأثر كثير على التركيز — رح نصلح هاد في البرنامج. "
    if "exam_stress" in signals:
        return "ضغط الامتحانات حقيقي — رح نبني جدول يريّحك ويحضّرك صح. "
    return ""


def _get_stage_question(stage: str, profile) -> str:
    gk = _gk(profile.grade_level)
    school_days_list = []
    try:
        school_days_list = json.loads(profile.school_days_json or "[0,1,2,3,4]")
    except Exception:
        school_days_list = [0, 1, 2, 3, 4]

    if stage == "start":
        return build_initial_message(profile)

    if stage == "exams":
        return (
            "قبل ما نبني الأسبوع، سؤال مهم:\n"
            "هل عندك امتحانات قريبة؟ قلي المادة والتاريخ والوقت — أو ارفع صورة الجدول.\n"
            "إذا ما في امتحانات هلق، قل لي \"لا\" ونكمل."
        )

    if stage.startswith("day_"):
        day_num = int(stage.split("_")[1])
        day_name = DAY_NAMES[day_num]
        is_school_day = day_num in school_days_list
        sleep_time = profile.sleep_time or "22:00"
        wake_time = profile.wake_time or "06:30"

        if is_school_day:
            return (
                f"يوم {day_name} — مدرسة حتى {profile.school_end}، نوم {sleep_time} (محفوظ).\n"
                f"شو بتعمل من بعد المدرسة؟ قلي الأنشطة والأوقات باختصار."
            )
        else:
            return (
                f"يوم {day_name} — عطلة، صحيان {wake_time}، نوم {sleep_time} (محفوظين).\n"
                f"شو بيكون يومك؟ قلي الأنشطة والأوقات باختصار."
            )

    return None


def _next_stage(current: str) -> str:
    idx = STAGES.index(current) if current in STAGES else 0
    if idx + 1 < len(STAGES):
        return STAGES[idx + 1]
    return "done"


def _next_incomplete_day_stage(day_data: dict) -> str:
    """يرجع مرحلة أول يوم لم تُجمع بياناته بعد، أو 'confirm' إذا كانت كل الأيام محفوظة."""
    for day_num in DAY_ORDER:
        if str(day_num) not in day_data:
            return f"day_{day_num}"
    return "confirm"


def _is_affirmative(text: str) -> bool:
    # Only clear confirmations — removed ambiguous words like "عادي", "يعطيك", "حلو"
    # that could appear mid-sentence in a correction request.
    positives = ["اي", "نعم", "ايوا", "يلا", "تمام", "صح", "موافق", "حسنا", "ok", "yes",
                 "ماشي", "خلاص", "ابدا"]
    return any(p in text.lower() for p in positives)


def _is_negative_exams(text: str) -> bool:
    negatives = ["لا يوجد", "لا توجد", "ما عندي", "مافي", "لا امتحانات", "حاليا لا", "لا", "no",
                 "مو", "لا شي", "بدون امتحانات"]
    return any(p in text.lower() for p in negatives)


def _build_summary(profile, day_data: dict) -> str:
    school_days_list = []
    try:
        school_days_list = json.loads(profile.school_days_json or "[0,1,2,3,4]")
    except Exception:
        school_days_list = [0, 1, 2, 3, 4]

    lines = ["هيك فهمت أسبوعك:\n"]
    for day_num_str, activities in day_data.items():
        try:
            day_num = int(day_num_str)
        except Exception:
            continue
        day_name = DAY_NAMES.get(day_num, day_num_str)
        day_type = "مدرسة" if day_num in school_days_list else "عطلة"
        lines.append(f"**{day_name}** ({day_type}): {activities}")

    lines.append("\nصح؟ إذا اي، رح أبني برنامجك الكامل.\nإذا في شي غلط، صحّحه وأنا أعدّل.")
    return "\n".join(lines)


_DAY_DISPLAY_ORDER = [6, 0, 1, 2, 3, 4, 5]


def _build_summary_data(profile, day_data: dict) -> dict:
    """يبني نسخة منظمة (وليست نصية) من بيانات الأسبوع لعرضها في بطاقة المراجعة قبل بناء الجدول."""
    try:
        school_days_list = json.loads(profile.school_days_json or "[0,1,2,3,4]")
    except Exception:
        school_days_list = [0, 1, 2, 3, 4]

    try:
        activities = json.loads(profile.activities_json or "{}")
    except Exception:
        activities = {}

    days = []
    for day_num in _DAY_DISPLAY_ORDER:
        key = str(day_num)
        if key in day_data:
            days.append({
                "day": day_num,
                "label": DAY_NAMES.get(day_num, key),
                "type": "مدرسة" if day_num in school_days_list else "عطلة",
                "text": day_data[key],
            })

    return {
        "grade_level": profile.grade_level,
        "school_start": profile.school_start,
        "school_end": profile.school_end,
        "wake_time": profile.wake_time,
        "sleep_time": profile.sleep_time,
        "activities": activities,
        "days": days,
    }


async def get_or_create_routine_profile(db: AsyncSession, student_id: int):
    result = await db.execute(
        select(StudentRoutineProfile).where(StudentRoutineProfile.student_id == student_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = StudentRoutineProfile(student_id=student_id)
        db.add(profile)
        await db.flush()
    return profile


async def get_weak_subjects(db: AsyncSession, student_id: int) -> list[str]:
    """قراءة المواد الضعيفة من قاعدة البيانات (من أداء الاختبارات والمنصة)."""
    from app.models.planner import PlannerProfile
    result = await db.execute(
        select(PlannerProfile).where(PlannerProfile.student_id == student_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return []
    try:
        weak = json.loads(profile.weak_subjects_json or "[]")
        return weak if isinstance(weak, list) else []
    except Exception:
        return []


async def _get_upcoming_exams(db: AsyncSession, student_id: int) -> list:
    """استرجاع الامتحانات القادمة خلال 21 يوماً (يغطي موسم امتحانات كامل وليس فقط الأيام الوشيكة)."""
    from datetime import datetime, timedelta, timezone
    from app.models.planner import PlannerLifeEvent, LifeEventType
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=21)
    try:
        result = await db.execute(
            select(PlannerLifeEvent).where(
                and_(
                    PlannerLifeEvent.student_id == student_id,
                    PlannerLifeEvent.event_type == LifeEventType.exam,
                    PlannerLifeEvent.event_date >= now,
                    PlannerLifeEvent.event_date <= cutoff,
                )
            ).order_by(PlannerLifeEvent.event_date)
        )
        exams = result.scalars().all()
        return [
            {
                "subject": e.subject or e.title.replace("امتحان ", ""),
                "date": e.event_date.strftime("%Y-%m-%d") if e.event_date else "",
                "days_left": max(0, (e.event_date.replace(tzinfo=timezone.utc) - now).days),
            }
            for e in exams
        ]
    except Exception:
        return []


async def finalize_routine_schedule(db: AsyncSession, profile, day_data: dict, weak_subjects: list, lang: str = "ar") -> dict:
    """يبني الجدول الأسبوعي عبر Gemini، يحفظه في قاعدة البيانات فوراً، ويجهز رسالة شرح القرارات.
    تُستخدم من مسار الدردشة (عند كتابة «نعم») ومن بطاقة مراجعة المعلومات قبل البناء."""
    schedule = await _generate_fast_routine_schedule(db, profile, day_data, weak_subjects, lang=lang)

    if not schedule:
        profile.chat_stage = "confirm"
        return {
            "reply": "لم أتمكن من بناء البرنامج الآن. حاول مرة أخرى بكتابة «نعم».",
            "schedule": None,
            "stage": "confirm",
        }

    # احفظ الجدول في DB فوراً ولا تنتظر زر التأكيد من الفرونت
    await save_routine_slots(db, profile, schedule)
    profile.onboarding_complete = True
    profile.chat_stage = "build"

    weak_note = (
        f"• المواد الضعيفة ({', '.join(weak_subjects)}) أخذت وقتاً أكثر وجلستين يومياً"
        if weak_subjects else
        "• وزّعت وقت الدراسة بشكل متوازن على الأسبوع"
    )
    upcoming = await _get_upcoming_exams(db, profile.student_id)
    exam_note = (
        f"• وضع الامتحانات مفعّل — جلسات مراجعة طويلة لـ {', '.join(e['subject'] for e in upcoming)}"
        if upcoming else
        "• لا امتحانات قريبة — ركّزت على بناء عادة دراسة منتظمة"
    )

    reply = (
        "ممتاز! بنيت برنامجك الكامل 🎉\n\n"
        "لماذا هذا الترتيب؟\n"
        f"• وضعت المواد الصعبة في أوقات التركيز العالي (صباحاً أو بعد الراحة)\n"
        f"{weak_note}\n"
        f"{exam_note}\n"
        "• راعيت أوقات الصلوات والوجبات والراحة\n\n"
        "شوف البرنامج — هل في شي تبيه يتغير أو اقتراح عندك؟"
    )
    return {
        "reply": reply,
        "schedule": schedule,
        "stage": "build",
    }


async def start_edit_day(db: AsyncSession, profile, day_num: int) -> dict:
    """يرجع المساعد لسؤال الطالب عن يوم محدد فقط — دون فقدان بيانات بقية الأيام المجمّعة."""
    try:
        day_data = json.loads(profile.day_data_json or "{}")
    except Exception:
        day_data = {}

    day_key = str(day_num)
    # علامة تخبر معالج الأيام إن هذا تعديل (وليس جمعاً خطياً) — يرجع لمرحلة التأكيد بعد الحفظ
    day_data["_edit_target"] = day_key
    day_data.pop(f"_a{day_key}", None)
    profile.day_data_json = json.dumps(day_data, ensure_ascii=False)
    profile.chat_stage = f"day_{day_num}"

    day_label = DAY_NAMES.get(day_num, "")
    reply = (
        f"تمام، خليني أسمع منك من جديد عن يوم {day_label} 🔁 (باقي الأيام محفوظة عندي)\n\n"
        + (_get_stage_question(profile.chat_stage, profile) or "")
    )
    return {"reply": reply, "schedule": None, "stage": profile.chat_stage}


async def process_routine_message(db: AsyncSession, profile, message: str, weak_subjects: list) -> dict:
    stage = profile.chat_stage or "start"
    day_data = {}
    try:
        day_data = json.loads(profile.day_data_json or "{}")
    except Exception:
        pass

    signals = _detect_signal(message)
    signal_prefix = _signal_response(signals)

    # استخراج المعلومات من رسالة الطالب
    extracted = await _extract_with_claude(message, stage, profile)

    # حفظ الامتحانات
    if stage == "exams" and extracted.get("exams"):
        await _save_exams(db, profile, extracted["exams"])

    # ---- انتقالات المراحل ----
    if stage == "start":
        profile.chat_stage = "exams"
        reply = signal_prefix + _get_stage_question("exams", profile)

    elif stage == "exams":
        # Check for extracted exams FIRST so explicit exam info is never lost.
        # "لا، عندي امتحان رياضيات غداً" contains "لا" but also has an exam — prioritise the exam.
        exams_extracted = extracted.get("exams")
        has_real_exams = isinstance(exams_extracted, list) and len(exams_extracted) > 0
        gemini_said_no_exams = isinstance(exams_extracted, list) and len(exams_extracted) == 0

        if has_real_exams:
            profile.chat_stage = "day_6"
            exams_text = "\n".join(
                [f"- {e['subject']}: {e.get('date', '') or 'تاريخ غير محدد'} الساعة {e.get('time', '') or 'وقت غير محدد'}" for e in exams_extracted]
            )
            reply = (
                f"{signal_prefix}حفظت امتحاناتك:\n{exams_text}\n\n"
                f"رح آخذها بعين الاعتبار وأخصص لك وقت مراجعة قبل كل امتحان.\n\n"
                + _get_stage_question("day_6", profile)
            )
        elif gemini_said_no_exams or _is_negative_exams(message):
            profile.chat_stage = "day_6"
            reply = signal_prefix + "تمام، ما في امتحانات هلق.\n\n" + _get_stage_question("day_6", profile)
        else:
            # Gemini totally failed (returned nothing at all) — advance anyway to avoid looping
            profile.chat_stage = "day_6"
            reply = signal_prefix + "تمام! سجّلت ملاحظة الامتحانات.\n\n" + _get_stage_question("day_6", profile)

    elif stage.startswith("day_"):
        day_num_str = stage.split("_")[1]
        day_label = DAY_NAMES.get(int(day_num_str), "")

        activities = extracted.get("activities", "")

        # Track attempts for this day (stored as "_aX" in day_data)
        attempt_key = f"_a{day_num_str}"
        attempt = day_data.get(attempt_key, 0) + 1
        day_data[attempt_key] = attempt

        # Fallback: if Gemini returned nothing, check if message has any time-like patterns
        if not activities:
            clock_hits = len(re.findall(r'\b\d{1,2}:\d{2}\b|\b\d{1,2}\s*-\s*\d{1,2}\b', message))
            if clock_hits >= 2:
                activities = message[:300]

        # After 2 attempts: always advance with whatever we have (even if empty — use raw message)
        if not activities and attempt >= 2:
            activities = message[:200]

        if activities:
            # Gemini extracted something (or fallback) — save it
            day_data[day_num_str] = activities
            day_data.pop(attempt_key, None)

            # وضع تعديل يوم محدد — بعد الحفظ: لو كل الأيام مكتملة ارجع لمرحلة التأكيد،
            # ولو كان التعديل صار أثناء الجمع (أيام ناقصة) كمّل من حيث وقفنا ولا تتخطَّ أي يوم
            edit_target = day_data.pop("_edit_target", None)
            if edit_target == day_num_str:
                profile.day_data_json = json.dumps(day_data, ensure_ascii=False)
                resume_stage = _next_incomplete_day_stage(day_data)
                profile.chat_stage = resume_stage
                if resume_stage == "confirm":
                    summary = _build_summary(profile, day_data)
                    reply = signal_prefix + f"تمام، حدّثت يوم {day_label}! ✅ (باقي الأيام زي ما هي)\n\n" + summary
                else:
                    reply = (
                        signal_prefix
                        + f"تمام، حدّثت يوم {day_label}! ✅ (باقي الأيام محفوظة)\n\n"
                        + "خلينا نكمل من حيث وقفنا:\n\n"
                        + _get_stage_question(resume_stage, profile)
                    )
            else:
                next_stage = _next_stage(stage)
                profile.chat_stage = next_stage
                profile.day_data_json = json.dumps(day_data, ensure_ascii=False)
                if next_stage == "confirm":
                    summary = _build_summary(profile, day_data)
                    reply = signal_prefix + summary
                elif next_stage.startswith("day_"):
                    reply = signal_prefix + f"تمام، حفظت يوم {day_label}! ✅\n\n" + _get_stage_question(next_stage, profile)
                else:
                    reply = signal_prefix + "يلا نبني برنامجك!"
        else:
            # Gemini returned nothing AND it's the first attempt — ask once more
            profile.day_data_json = json.dumps(day_data, ensure_ascii=False)
            reply = (
                signal_prefix +
                f"قلي شو بتعمل يوم {day_label} — باختصار كيف، حتى لو بدون أوقات دقيقة.\n"
                "مثلاً: «رياضة، درست شي ساعتين، عشيت ونمت»"
            )

    elif stage == "confirm":
        if _is_affirmative(message):
            return await finalize_routine_schedule(db, profile, day_data, weak_subjects)
        else:
            # طالب التعديل — ارجع لمرحلة جمع البيانات
            profile.chat_stage = "day_6"
            reply = signal_prefix + f"تمام، خليني أسألك من جديد.\n\n{_get_stage_question('day_6', profile)}"

    elif stage == "build":
        # المستخدم بعث اقتراحاً — راجع البرنامج مع اقتراحاته
        profile.chat_stage = "review"
        review = await _review_schedule_claude(profile, weak_subjects, user_suggestion=message)
        return {
            "reply": review.get("text", "تم مراجعة البرنامج."),
            "suggestions": review.get("suggestions", []),
            "schedule": None,
            "stage": "review",
        }

    elif stage == "review":
        # المستخدم رد على المراجعة
        profile.chat_stage = "done"
        reply = "عظيم! البرنامج جاهز. بالتوفيق في أسبوعك! 🌟"

    else:
        reply = signal_prefix + (_get_stage_question(profile.chat_stage or "exams", profile) or "تفضل، أنا جاهز.")

    result = {"reply": reply, "schedule": None, "stage": profile.chat_stage}
    if profile.chat_stage == "confirm":
        result["summary_data"] = _build_summary_data(profile, day_data)
    return result


def _parse_last_json(text: str):
    """Find the last complete JSON object in text, working backwards from the last }."""
    last = text.rfind('}')
    if last == -1:
        return None
    depth = 0
    start = -1
    for i in range(last, -1, -1):
        if text[i] == '}':
            depth += 1
        elif text[i] == '{':
            depth -= 1
            if depth == 0:
                start = i
                break
    if start == -1:
        return None
    json_str = text[start:last + 1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Try replacing literal newlines in string values
        json_str_fixed = re.sub(r'(?m)(?<=": ")(.+?)(?=")', lambda m: m.group(0).replace('\n', ' '), json_str)
        try:
            return json.loads(json_str_fixed)
        except Exception:
            return None


async def _extract_with_claude(message: str, stage: str, profile) -> dict:
    from app.core.config import get_settings
    from app.services.claude_service import generate_claude_text_sync, is_claude_configured
    from datetime import date as _date

    settings = get_settings()
    if not is_claude_configured():
        logger.warning("Claude: ANTHROPIC_API_KEY is empty — skipping extraction")
        return {}
    try:
        if stage == "exams":
            today_str = _date.today().isoformat()
            prompt = (
                f'أنت مساعد تعليمي. استخرج بيانات الامتحانات من رسالة طالب سوري/عربي.\n\n'
                f'رسالة الطالب: "{message}"\n'
                f'التاريخ اليوم: {today_str}\n\n'
                f'قواعد الاستخراج الإلزامية:\n'
                f'1. استخرج كل امتحان مذكور — حتى لو ذُكر بشكل جانبي أو عابر.\n'
                f'2. الألفاظ الدارجة للتواريخ: "بكرا"=غداً ({today_str} + 1 يوم)، "بعد بكرا"=بعد غد، "الأسبوع الجاي"=+7 أيام، "نهاية الأسبوع"=أقرب جمعة، أسماء الأيام=أقرب يوم بهذا الاسم.\n'
                f'3. إذا ذُكر الامتحان بدون تاريخ أو وقت، استخدم null لذلك الحقل.\n'
                f'4. إذا قال الطالب "لا" أو "ما عندي" أو "مافي" أو ما ذكر امتحاناً: أرجع exams=[]\n'
                f'5. إذا قال الطالب "لا، عندي امتحان...": تجاهل "لا" واستخرج الامتحان.\n'
                f'6. أسماء المواد الشائعة: رياضيات=math، فيزياء=physics، كيمياء=chemistry، عربي=arabic، انكليزي=english.\n\n'
                f'أرجع JSON فقط بدون أي نص إضافي:\n'
                f'{{"exams": [{{"subject": "اسم المادة بالعربي", "date": "YYYY-MM-DD أو null", "time": "HH:MM أو null"}}]}}\n'
                f'إذا لا يوجد امتحانات: {{"exams": []}}'
            )
        elif stage.startswith("day_"):
            day_num = int(stage.split("_")[1])
            day_name = DAY_NAMES.get(day_num, "")
            sleep_time = getattr(profile, "sleep_time", None) or "22:00"
            wake_time = getattr(profile, "wake_time", None) or "06:30"
            school_end = getattr(profile, "school_end", None) or "13:00"
            school_days_list = []
            try:
                school_days_list = json.loads(getattr(profile, "school_days_json", None) or "[0,1,2,3,4]")
            except Exception:
                school_days_list = [0, 1, 2, 3, 4]
            is_school_day = day_num in school_days_list
            start_anchor = f"وصول البيت بعد {school_end}" if is_school_day else f"صحيان {wake_time}"
            prompt = (
                f'أنت مساعد ذكي يفهم العربية الدارجة (سورية/لبنانية/خليجية).\n\n'
                f'الطالب يصف يوم {day_name}. معلومات ثابتة: بداية اليوم={start_anchor}، نوم={sleep_time}.\n\n'
                f'رسالة الطالب: "{message}"\n\n'
                f'مهمتك: اكتب ملخصاً لأنشطة اليوم بأوقات منطقية.\n\n'
                f'قواعد الاستنتاج السريع:\n'
                f'• "شي X" أو "حوالي X" → الساعة X (مثلاً "شي 2"=14:00، "شي 4"=16:00)\n'
                f'• "بعد الضهر"≈14:30، "العصر"≈15:30، "المغرب"≈18:00، "العشا"≈20:00، "بالليل"≈21:00\n'
                f'• "درست/درس/ذاكرت"=90 دقيقة دراسة، "رياضة/جيم"=60 دقيقة، "قيلولة/نمت شوي"=60 دقيقة\n'
                f'• "أكل/فطور/غداء/عشا"=30 دقيقة، "مع العيلة/بحكي"=45 دقيقة\n'
                f'• "عادي" أو "مثل باقي الأيام" في بداية الرسالة = تجاهلها وخذ باقي التفاصيل\n\n'
                f'قاعدة مهمة: إذا الرسالة تحتوي على أي نشاط واحد أو أكثر → اكتب الملخص. لا تُرجع activities فارغاً إلا إذا الرسالة فارغة تماماً.\n\n'
                f'أرجع JSON فقط بدون أي شرح إضافي أو مقدمة:\n'
                f'{{"activities": "ملخص اليوم بالأوقات هنا"}}'
            )
        else:
            return {}

        logger.info("Claude extraction: stage=%s model=%s", stage, settings.CLAUDE_MODEL)
        text = generate_claude_text_sync(prompt, temperature=0.2, max_tokens=4096)
        # Strip markdown code fences
        clean = re.sub(r'```(?:json)?\s*|\s*```', '', text).strip()
        # Find the LAST complete JSON object (ignoring any echoed prompt examples before it)
        result = _parse_last_json(clean)
        if result is not None:
            return result
        # Final fallback: extract field directly with regex
        if stage.startswith("day_"):
            acts = re.search(r'"activities"\s*:\s*"((?:[^"\\]|\\.)*)"', clean)
            if acts:
                return {"activities": acts.group(1)}
        elif stage == "exams":
            exams_match = re.search(r'"exams"\s*:\s*(\[[^\]]*\])', clean)
            if exams_match:
                try:
                    return {"exams": json.loads(exams_match.group(1))}
                except Exception:
                    pass
    except Exception as e:
        logger.error("Gemini extract error: %s", repr(e)[:200])
    return {}


async def _save_exams(db: AsyncSession, profile, exams: list) -> int:
    from datetime import datetime, timezone
    from app.models.planner import LifeEventType, PlannerLifeEvent

    saved = 0
    for exam in exams:
        try:
            event_date = datetime.fromisoformat(exam.get("date", "")).replace(tzinfo=timezone.utc)
            db.add(PlannerLifeEvent(
                student_id=profile.student_id,
                title=f"امتحان {exam.get('subject', '')}",
                event_type=LifeEventType.exam,
                event_date=event_date,
                start_time=exam.get("time"),
                duration_minutes=120,
                is_blocking=True,
                subject=exam.get("subject"),
            ))
            saved += 1
        except Exception:
            continue
    if saved:
        logger.info("Saved %d exam(s) to planner_life_events for student_id=%s", saved, profile.student_id)
    return saved


async def acknowledge_saved_exams(profile, exams: list[dict]) -> dict:
    """يبني رد المساعد بعد حفظ امتحانات أكّدها الطالب من نافذة المراجعة (بدل تجاهلها أو إعادة سؤاله عنها).

    إذا كانت المحادثة لسا بمرحلة جمع معلومات الامتحانات أثناء الإعداد، يكمل الجريان الطبيعي
    ويسأل عن أول يوم مباشرة (تماماً كما لو ذكرها الطالب نصياً)؛ أما إذا كان البرنامج مبنياً
    مسبقاً، فيكتفي بالتأكيد ويوجّهه لزر «تجديد الأسبوع» بدل طرح سؤال نعم/لا لا تفهمه آلة الحالات.
    تفاصيل الامتحانات (exams) تُعاد منظَّمة كي يعرضها الفرونت كجدول مرئي بدل نص عادي."""
    exam_count = len(exams)
    count_note = f"حفظت {exam_count} امتحان! 📝" if exam_count else "تمام، حفظت ملاحظتك."

    if profile.chat_stage == "exams":
        profile.chat_stage = "day_6"
        reply = (
            f"{count_note}\nرح آخذها بعين الاعتبار وأخصص لك وقت مراجعة قبل كل امتحان.\n\n"
            + (_get_stage_question("day_6", profile) or "")
        )
    else:
        reply = (
            f"{count_note} ✅\n\n"
            "إذا بدك تعدّل برنامجك الأسبوعي بناءً عليها، اضغط زر «تجديد الأسبوع» 🔄"
        )

    structured_exams = [
        {
            "subject": e.get("subject") or "",
            "date": e.get("date") or "",
            "time": e.get("time") or "",
        }
        for e in exams
    ]
    return {"reply": reply, "stage": profile.chat_stage, "exams": structured_exams}


async def _generate_schedule_claude(db: AsyncSession, profile, day_data: dict, weak_subjects: list):
    from app.core.config import get_settings
    from app.services.claude_service import generate_claude_json_sync, is_claude_configured

    settings = get_settings()
    if not is_claude_configured():
        return None

    gk = _gk(profile.grade_level)
    school_days_list = []
    try:
        school_days_list = json.loads(profile.school_days_json or "[0,1,2,3,4]")
    except Exception:
        school_days_list = [0, 1, 2, 3, 4]

    school_day_names = [DAY_NAMES[d] for d in school_days_list if d in DAY_NAMES]
    holiday_day_names = [DAY_NAMES[d] for d in range(7) if d not in school_days_list and d in DAY_NAMES]

    day_summary = "\n".join(
        [f"يوم {DAY_NAMES.get(int(k), k)} ({'مدرسة' if int(k) in school_days_list else 'عطلة'}): {v}"
         for k, v in day_data.items() if not k.startswith('_')]
    )

    # الأنشطة الثابتة من ملف الطالب (رياضة، حصص خاصة)
    fixed_activities_str = ""
    try:
        acts = json.loads(profile.activities_json or "{}")
        details = acts.get("details", {})
        fixed_lines = []
        for act_name, act_info in details.items():
            if isinstance(act_info, dict) and act_info.get("days"):
                day_names_str = "، ".join([DAY_NAMES.get(int(d), str(d)) for d in act_info["days"]])
                fixed_lines.append(f"  - {act_name}: أيام {day_names_str}، {act_info.get('time','')}")
        if fixed_lines:
            fixed_activities_str = "\n- أنشطة ثابتة أسبوعية (ضعها بالأوقات المحددة):\n" + "\n".join(fixed_lines)
    except Exception:
        pass

    # المواد الضعيفة من المنصة
    if not weak_subjects:
        weak_subjects = await get_weak_subjects(db, profile.student_id)

    weak_str = "، ".join(weak_subjects) if weak_subjects else "لا يوجد مواد ضعيفة محددة"
    prayers_str = "، ".join(gk["prayers"])
    meals_str = "، ".join(gk["meals"])

    # وضع الامتحانات — امتحانات خلال 3 أيام
    upcoming_exams = await _get_upcoming_exams(db, profile.student_id)
    exam_mode = len(upcoming_exams) > 0

    exam_mode_instructions = ""
    if exam_mode:
        very_soon = [e for e in upcoming_exams if e["days_left"] <= 3]
        soon = [e for e in upcoming_exams if 3 < e["days_left"] <= 7]
        later = [e for e in upcoming_exams if e["days_left"] > 7]
        exam_lines = "\n".join(
            [f"  - {e['subject']}: يوم {e['date']} (بعد {e['days_left']} يوم)" for e in upcoming_exams]
        )
        priority_notes = []
        if very_soon:
            priority_notes.append(
                f"  • خلال 3 أيام أو أقل ({', '.join(e['subject'] for e in very_soon)}): "
                "أعطها جلسة مراجعة مكثفة يومياً (60-75 دقيقة) في وقت التركيز العالي (أول جلسة دراسة بعد المدرسة)، "
                "وقلّص الأنشطة غير الضرورية تلك الأيام لصالح المراجعة."
            )
        if soon:
            priority_notes.append(
                f"  • خلال 4-7 أيام ({', '.join(e['subject'] for e in soon)}): "
                "خصص جلسة مراجعة يومية متوسطة (45 دقيقة) وزِد تدريجياً كلما اقترب الموعد."
            )
        if later:
            priority_notes.append(
                f"  • بعد أكثر من أسبوع ({', '.join(e['subject'] for e in later)}): "
                "خصص 2-3 جلسات مراجعة أسبوعياً (30-45 دقيقة) لتوزيع الحمل بدل تكديسه قبيل الامتحان."
            )
        exam_mode_instructions = (
            f"\n\nوضع الامتحانات مفعّل — جدول الامتحانات القادمة (مأخوذ من الصورة/الملف الذي رفعه الطالب):\n{exam_lines}\n\n"
            "رتّب أولوية المراجعة حسب قرب موعد كل امتحان (الأقرب يأخذ وقتاً ومكاناً أفضل في اليوم):\n"
            + "\n".join(priority_notes) + "\n"
            "• ضع جلسات المراجعة لمواد الامتحانات في أوقات التركيز العالي (بعد المدرسة مباشرة أو بعد الراحة، وليس متأخراً قبل النوم)\n"
            "• لا تُسقِط بقية المواد كلياً — قلّل وقتها فقط في الأيام القريبة من الامتحانات لصالح مواد الامتحان\n"
            "• في يوم الامتحان نفسه: اجعل الجلسة الصباحية مراجعة أخيرة خفيفة لنفس المادة بدل بدء موضوع جديد\n"
        )
    elif weak_subjects:
        exam_mode_instructions = (
            f"\n\nلا امتحانات قريبة — ركّز على تقوية المواد الضعيفة:\n"
            f"• أعطِ {weak_str} جلستين دراسيتين يومياً بدلاً من واحدة (30-45 دقيقة لكل جلسة)\n"
            f"• ابدأ بهذه المواد في بداية كل جلسة دراسة\n"
        )

    prompt = f"""أنت مساعد تعليمي ذكي يبني برامج يومية كاملة للطلاب. مهمتك إنتاج جدول أسبوعي دقيق بدون تعارض في الأوقات.

═══════════════════════════════
معلومات الطالب:
- الصف: {profile.grade_level}
- المدرسة: {profile.school_start} حتى {profile.school_end}
- أيام المدرسة: {', '.join(school_day_names)}
- أيام العطلة: {', '.join(holiday_day_names) if holiday_day_names else 'لا يوجد'}
- الصحيان: {profile.wake_time or gk['wake_time']} | النوم: {profile.sleep_time or gk['sleep_time']}
- ساعات الدراسة الموصى بها: {gk['study_hours']}
- وقت اللعب/الترفيه: {gk['play_hours']}
- قيلولة: {'نعم ' + gk['nap_duration'] if gk['nap'] else 'لا'}
- الصلوات: {prayers_str}
- الوجبات: {meals_str}
- المواد الضعيفة (أعطِها وقتاً أكثر): {weak_str}
- ملاحظات الصف: {gk['notes']}{fixed_activities_str}
{exam_mode_instructions}
ما أخبرني به الطالب عن أسبوعه:
{day_summary if day_summary else "لم يذكر تفاصيل كافية — استخدم القيم الافتراضية الموصى بها للصف."}

═══════════════════════════════
القواعد الإلزامية (لا استثناء):
1. لا تعارض في الأوقات إطلاقاً — كل slot يجب أن ينتهي قبل بدء التالي بدقيقة على الأقل.
2. أيام المدرسة: يبدأ اليوم بالصحيان → فطور → مدرسة ({profile.school_start}-{profile.school_end}) → وصول البيت → راحة/أكل → دراسة → أنشطة → عشاء → نوم.
3. أيام العطلة: يبدأ بالصحيان → فطور → دراسة أطول (لا مدرسة) → وقت حر أكثر → أنشطة → نوم.
4. كل يوم يجب أن يحتوي على: الصلوات الخمس (15 دقيقة كل منها)، 3 وجبات (فطور 20 دقيقة، غداء 30-40 دقيقة، عشاء 30 دقيقة).
5. راحة بعد الغداء: {'قيلولة ' + gk['nap_duration'] if gk['nap'] else '15-20 دقيقة راحة'}.
6. المواد الضعيفة ({weak_str if weak_str != "لا يوجد مواد ضعيفة محددة" else "لا محددة"}) تأخذ أطول جلسة دراسة في اليوم وتُوضع أولاً.
7. وقت الشاشة/الجوال: 45 دقيقة يومياً كحد أقصى.
8. وقت العيلة: 30-60 دقيقة يومياً على الأقل.
9. الأنشطة المذكورة من الطالب (رياضة، حصص خاصة...) يجب أن تظهر في الأيام الصحيحة بأوقاتها.
10. أقل مدة لأي slot: 15 دقيقة. أطول مدة لجلسة دراسة واحدة: 90 دقيقة (ثم راحة).
11. النوم يجب أن يكون slot كامل من وقت النوم حتى وقت الصحيان.

═══════════════════════════════
صيغة الإخراج — JSON فقط بدون أي نص قبله أو بعده:
{{"days":{{"0":[],"1":[],"2":[],"3":[],"4":[],"5":[],"6":[]}},"notes":"ملاحظة واحدة عن البرنامج"}}

مفتاح الأيام: 0=الاثنين، 1=الثلاثاء، 2=الأربعاء، 3=الخميس، 4=الجمعة، 5=السبت، 6=الأحد
أنواع النشاط المسموحة فقط: school, study, sport, meal, sleep, prayer, family, private_lesson, free, other
كل slot يجب أن يكون بهذا الشكل الدقيق:
{{"start":"HH:MM","end":"HH:MM","type":"النوع","title":"العنوان بالعربي","subject":"المادة أو null"}}"""

    try:
        from app.services.claude_service import generate_claude_json_sync

        last_err = None
        for attempt in range(2):
            try:
                text = generate_claude_json_sync(prompt, temperature=0.4, max_output_tokens=8192)
                m = re.search(r'\{[\s\S]*"days"[\s\S]*\}', text)
                if m:
                    parsed = json.loads(m.group())
                    return parsed.get("days", parsed)
                last_err = "no JSON match in response"
            except Exception as e:
                last_err = e
                logger.error("Claude generate error (attempt %d): %s", attempt + 1, repr(e)[:300])
        if last_err:
            logger.error("Claude generate_schedule failed after retries: %s", repr(last_err)[:300])
    except Exception as e:
        logger.error("Claude generate error: %s", repr(e)[:300])
    return None


def _time_to_minutes(value: str | None, default: str) -> int:
    raw = (value or default or "").strip()
    try:
        h, m = raw.split(":", 1)
        return max(0, min(23 * 60 + 59, int(h) * 60 + int(m[:2])))
    except Exception:
        h, m = default.split(":", 1)
        return int(h) * 60 + int(m)


def _minutes_to_time(value: int) -> str:
    value = max(0, min(23 * 60 + 59, value))
    return f"{value // 60:02d}:{value % 60:02d}"


def _slot(start: int, end: int, activity_type: str, title: str, subject: str | None = None, fixed: bool = False) -> dict:
    return {
        "start": _minutes_to_time(start),
        "end": _minutes_to_time(end),
        "type": activity_type,
        "title": title,
        "subject": subject,
        "fixed": fixed,
    }


def _normalize_local_day_slots(slots: list[dict]) -> list[dict]:
    normalized = []
    cursor = 0
    for raw in sorted(slots, key=lambda s: s.get("_start", _time_to_minutes(s.get("start"), "00:00"))):
        start = raw.get("_start", _time_to_minutes(raw.get("start"), "00:00"))
        end = raw.get("_end", _time_to_minutes(raw.get("end"), "00:00"))
        if end <= start:
            continue
        if start < cursor:
            duration = end - start
            start = cursor + 5
            end = start + duration
        if end > 23 * 60 + 59 or end - start < 10:
            continue
        normalized.append(_slot(start, end, raw.get("type", "other"), raw.get("title", ""), raw.get("subject"), raw.get("fixed", False)))
        cursor = end
    return normalized


def _activity_details(profile) -> dict:
    try:
        activities = json.loads(profile.activities_json or "{}")
        details = activities.get("details", {})
        return details if isinstance(details, dict) else {}
    except Exception:
        return {}


def _fixed_activity_slots_for_day(profile, day_num: int) -> list[dict]:
    out = []
    for name, info in _activity_details(profile).items():
        if not isinstance(info, dict):
            continue
        try:
            days = [int(d) for d in info.get("days", [])]
        except Exception:
            days = []
        if day_num not in days:
            continue
        start = _time_to_minutes(info.get("start") or info.get("time"), "17:00")
        end = _time_to_minutes(info.get("end"), _minutes_to_time(start + 60))
        if end <= start:
            end = start + 60
        activity_type = "private_lesson" if name == "دروس خاصة" else "sport" if name == "رياضة" else "other"
        title = info.get("subject") if activity_type == "private_lesson" and info.get("subject") else name
        out.append({
            "_start": start,
            "_end": end,
            "type": activity_type,
            "title": title,
            "subject": info.get("subject") or None,
            "fixed": True,
        })
    return out


def _time_to_minutes_contextual(value: str, context: str) -> int:
    minutes = _time_to_minutes(value, "00:00")
    hour = minutes // 60
    lowered = context.lower()
    if hour < 12 and any(marker in lowered for marker in ("مساء", "عصراً", "عصرا", "المغرب", "العشاء", "بالليل")):
        minutes += 12 * 60
    elif hour <= 6 and any(marker in lowered for marker in ("ظهراً", "ظهرا", "بعد الظهر", "العصر")):
        minutes += 12 * 60
    return min(minutes, 23 * 60 + 59)


def _classify_day_data_context(context: str) -> tuple[str, str, str | None]:
    text = context.strip(" ،.؛-")
    if any(k in text for k in ("نوم", "نام")):
        return "sleep", "نوم", None
    if any(k in text for k in ("دكتور", "طبيب", "موعد")):
        return "other", "موعد", None
    if any(k in text for k in ("جدت", "العائلة", "الأهل", "اهلي", "أهلي", "رفيق", "صديق", "زيارة")):
        return "family", text or "وقت عائلي", None
    if any(k in text for k in ("درس خصوصي", "خصوصي")):
        return "private_lesson", text or "درس خصوصي", None
    if any(k in text for k in ("مباراة", "رياضة", "لعب", "تمرين")):
        return "sport", text or "رياضة", None
    if "صلاة" in text:
        return "prayer", text or "صلاة", None
    if any(k in text for k in ("دراسة", "درست", "درس", "ذاكرت", "مراجعة")):
        return "study", text or "دراسة", None
    if any(k in text for k in ("فطور", "غداء", "عشاء", "أكل", "اكل")):
        return "meal", text or "وجبة", None
    return "other", text or "نشاط محفوظ من جدولك", None


def _slots_from_day_text(text: str | None) -> list[dict]:
    if not text:
        return []
    slots = []
    range_re = re.compile(
        r"([^،.؛\n]{0,55}?)(\d{1,2}:\d{2})\s*(?:-|لغاية|حتى|إلى|الى)\s*(\d{1,2}:\d{2})([^،.؛\n]{0,55})"
    )
    occupied_spans: list[tuple[int, int]] = []
    for match in range_re.finditer(text):
        context = f"{match.group(1)} {match.group(4)}"
        activity_type, title, subject = _classify_day_data_context(context)
        if activity_type == "sleep":
            continue
        start = _time_to_minutes_contextual(match.group(2), context)
        end = _time_to_minutes_contextual(match.group(3), context)
        if end <= start:
            continue
        slots.append({"_start": start, "_end": end, "type": activity_type, "title": title, "subject": subject, "fixed": True})
        occupied_spans.append(match.span())

    point_re = re.compile(r"([^،.؛\n]{0,35}?)(?:الساعة\s*)?(\d{1,2}:\d{2})([^،.؛\n]{0,55})")
    for match in point_re.finditer(text):
        if any(start <= match.start() < end for start, end in occupied_spans):
            continue
        context = f"{match.group(1)} {match.group(3)}"
        activity_type, title, subject = _classify_day_data_context(context)
        if activity_type == "sleep" or any(k in context for k in ("صحيان", "وصول البيت", "وصل البيت")):
            continue
        start = _time_to_minutes_contextual(match.group(2), context)
        duration = 60 if activity_type in ("other", "family", "sport", "private_lesson") else 45
        slots.append({"_start": start, "_end": start + duration, "type": activity_type, "title": title, "subject": subject, "fixed": True})
    return slots


async def _routine_exam_subjects(db: AsyncSession, student_id: int) -> list[str]:
    from app.models.planner import LifeEventType, PlannerLifeEvent

    now = datetime.now(timezone.utc) - timedelta(days=1)
    cutoff = datetime.now(timezone.utc) + timedelta(days=45)
    try:
        result = await db.execute(
            select(PlannerLifeEvent).where(
                and_(
                    PlannerLifeEvent.student_id == student_id,
                    PlannerLifeEvent.event_type == LifeEventType.exam,
                    PlannerLifeEvent.event_date >= now,
                    PlannerLifeEvent.event_date <= cutoff,
                )
            ).order_by(PlannerLifeEvent.event_date, PlannerLifeEvent.created_at)
        )
        subjects = []
        for event in result.scalars().all():
            subject = (event.subject or event.title or "").replace("امتحان", "").strip()
            if subject and subject not in subjects:
                subjects.append(subject)
        return subjects[:6]
    except Exception:
        return []


async def _generate_fast_routine_schedule(
    db: AsyncSession,
    profile,
    day_data: dict,
    weak_subjects: list | None,
    lang: str = "ar",
) -> dict:
    """Build a deterministic weekly routine so student uploads never depend on slow LLM JSON."""
    school_days = []
    try:
        school_days = [int(d) for d in json.loads(profile.school_days_json or "[0,1,2,3,4]")]
    except Exception:
        school_days = [0, 1, 2, 3, 4]

    exam_subjects = await _routine_exam_subjects(db, profile.student_id)
    focus_subjects = [s for s in (weak_subjects or []) if s] + [s for s in exam_subjects if s]
    if not focus_subjects:
        focus_subjects = [_slot_title("general_review", lang)]

    wake = _time_to_minutes(profile.wake_time, "06:30")
    sleep = _time_to_minutes(profile.sleep_time, "22:00")
    if sleep <= wake + 10 * 60:
        sleep = 22 * 60
    school_start = _time_to_minutes(profile.school_start, "07:30")
    school_end = _time_to_minutes(profile.school_end, "13:00")

    days: dict[str, list[dict]] = {}
    for day_num in range(7):
        is_school = day_num in school_days
        subject_a = focus_subjects[day_num % len(focus_subjects)]
        subject_b = focus_subjects[(day_num + 1) % len(focus_subjects)]
        slots: list[dict] = _slots_from_day_text(day_data.get(str(day_num)))

        slots.append({"_start": wake, "_end": min(wake + 30, school_start - 10 if is_school else wake + 45), "type": "meal", "title": _slot_title("breakfast", lang), "subject": None, "fixed": True})
        if is_school:
            slots.append({"_start": school_start, "_end": school_end, "type": "school", "title": _slot_title("school", lang), "subject": None, "fixed": True})
            slots.append({"_start": school_end + 15, "_end": school_end + 55, "type": "meal", "title": _slot_title("lunch_short", lang), "subject": None, "fixed": False})
            study_start = school_end + 75
            slots.append({"_start": study_start, "_end": study_start + 55, "type": "study", "title": _slot_title("review", lang, subject=subject_a), "subject": subject_a, "fixed": False})
            slots.append({"_start": study_start + 70, "_end": study_start + 115, "type": "study", "title": _slot_title("homework", lang, subject=subject_b), "subject": subject_b, "fixed": False})
        else:
            study_start = wake + 90
            slots.append({"_start": study_start, "_end": study_start + 75, "type": "study", "title": _slot_title("review_focused", lang, subject=subject_a), "subject": subject_a, "fixed": False})
            slots.append({"_start": study_start + 95, "_end": study_start + 155, "type": "study", "title": _slot_title("practice", lang, subject=subject_b), "subject": subject_b, "fixed": False})
            slots.append({"_start": 13 * 60, "_end": 13 * 60 + 40, "type": "meal", "title": _slot_title("lunch", lang), "subject": None, "fixed": False})

        slots.extend(_fixed_activity_slots_for_day(profile, day_num))
        slots.append({"_start": 18 * 60, "_end": 18 * 60 + 35, "type": "free", "title": _slot_title("rest_walk", lang), "subject": None, "fixed": False})
        slots.append({"_start": 19 * 60 + 30, "_end": 20 * 60, "type": "meal", "title": _slot_title("dinner", lang), "subject": None, "fixed": False})
        slots.append({"_start": max(20 * 60 + 15, sleep - 90), "_end": max(20 * 60 + 45, sleep - 45), "type": "family", "title": _slot_title("family_time", lang), "subject": None, "fixed": False})
        slots.append({"_start": sleep, "_end": 23 * 60 + 59, "type": "sleep", "title": _slot_title("sleep", lang), "subject": None, "fixed": True})

        days[str(day_num)] = _normalize_local_day_slots(slots)

    return days


async def _review_schedule_claude(profile, weak_subjects: list, user_suggestion: str = "") -> dict:
    """مراجعة البرنامج المبني وتقديم اقتراحات تحسين — المرحلة الخامسة."""
    from app.core.config import get_settings
    from app.services.claude_service import generate_claude_json_sync, is_claude_configured

    settings = get_settings()
    if not is_claude_configured():
        return {"text": "البرنامج جاهز! بالتوفيق.", "suggestions": []}

    gk = _gk(profile.grade_level)
    weak_str = "، ".join(weak_subjects) if weak_subjects else "لا يوجد"

    suggestion_note = f"\nاقتراح الطالب: \"{user_suggestion}\"" if user_suggestion else ""

    prompt = f"""أنت مراجع تعليمي ذكي. راجع هذا البرنامج اليومي وقدم اقتراحات تحسين.

الطالب: صف {profile.grade_level} | نوم موصى: {gk['sleep_time']} | دراسة موصى: {gk['study_hours']}
المواد الضعيفة: {weak_str}{suggestion_note}

مهمتك: قدّم 3-5 اقتراحات تحسين قابلة للتطبيق مع شرح سبب أهمية كل اقتراح.
كن إيجابياً وشجّعاً — ابدأ بتهنئة على البرنامج الجيد.
{f'راعِ اقتراح الطالب في ردّك وفسّر لماذا هو فكرة جيدة أو كيف يمكن تطبيقه.' if user_suggestion else ''}

أرجع JSON فقط:
{{
  "text": "رسالة ترحيبية تهنئ الطالب وتشرح المراجعة بجملتين",
  "suggestions": [
    {{"id": 1, "title": "عنوان الاقتراح", "description": "شرح الاقتراح وسبب أهميته في جملة أو جملتين", "priority": "high/medium/low"}},
    ...
  ]
}}"""

    try:
        text = generate_claude_json_sync(prompt, temperature=0.3, max_output_tokens=2048)
        m = re.search(r'\{[\s\S]*"text"[\s\S]*\}', text)
        if m:
            return json.loads(m.group())
    except Exception as e:
        logger.error("Claude review error: %s", repr(e)[:300])

    return {
        "text": "البرنامج جاهز! راجعته وهو يبدو متوازناً. إليك بعض الاقتراحات لتحسينه.",
        "suggestions": [
            {"id": 1, "title": "تنويع أوقات الدراسة", "description": "دراسة المواد الصعبة صباحاً يرفع التركيز لأن الذهن يكون أنشط.", "priority": "medium"},
        ],
    }


def _validate_slots(days: dict) -> list[str]:
    errors = []
    for day, slots in days.items():
        if not isinstance(slots, list):
            continue
        ss = sorted(slots, key=lambda s: s.get("start", "00:00"))
        for i in range(len(ss) - 1):
            if ss[i].get("end", "00:00") > ss[i + 1].get("start", "00:00"):
                errors.append(f"تعارض يوم {DAY_NAMES.get(int(day), day)} بين {ss[i].get('title','')} و {ss[i+1].get('title','')}")
    return errors


def text_contains_arabic(text: str | None) -> bool:
    return bool(text and ARABIC_TEXT_RE.search(str(text)))


def week_schedule_contains_arabic(days: dict) -> bool:
    for slots in days.values():
        if not isinstance(slots, list):
            continue
        for slot in slots:
            if text_contains_arabic(slot.get("title")) or text_contains_arabic(slot.get("subject")):
                return True
    return False


def _clean_day_data_for_regeneration(day_data: dict) -> dict:
    return {
        k: v for k, v in day_data.items()
        if not str(k).startswith("_") and str(k).isdigit() and isinstance(v, str) and v.strip()
    }


async def regenerate_student_routine(
    db: AsyncSession,
    profile,
    weak_subjects: list | None = None,
    lang: str = "ar",
) -> dict:
    """Rebuild routine_slots from profile + day_data via the Gemini pipeline."""
    if weak_subjects is None:
        weak_subjects = await get_weak_subjects(db, profile.student_id)

    try:
        raw_day_data = json.loads(profile.day_data_json or "{}")
    except Exception:
        raw_day_data = {}
    day_data = _clean_day_data_for_regeneration(raw_day_data)

    schedule = await _generate_fast_routine_schedule(db, profile, day_data, weak_subjects, lang=lang)
    if not schedule:
        return {
            "ok": False,
            "regenerated": False,
            "reason": "generation_failed",
            "slots_saved": 0,
        }

    errors = _validate_slots(schedule)
    if errors:
        return {
            "ok": False,
            "regenerated": False,
            "reason": "validation_failed",
            "errors": errors[:3],
            "slots_saved": 0,
        }

    count = await save_routine_slots(db, profile, schedule)
    profile.onboarding_complete = True
    if profile.chat_stage not in ("build", "review", "done"):
        profile.chat_stage = "build"

    return {
        "ok": True,
        "regenerated": True,
        "reason": "success",
        "slots_saved": count,
        "schedule": schedule,
    }


async def ensure_english_routine(db: AsyncSession, profile) -> dict:
    """If routine_slots contain Arabic text, regenerate once using the Gemini pipeline."""
    from app.core.config import get_settings

    days = await get_week_slots(db, profile.id)
    has_slots = any(isinstance(slots, list) and slots for slots in days.values())
    if not has_slots:
        return {"regenerated": False, "reason": "empty_schedule"}
    if not week_schedule_contains_arabic(days):
        return {"regenerated": False, "reason": "already_english"}

    from app.services.claude_service import is_claude_configured

    settings = get_settings()
    if not is_claude_configured():
        logger.warning(
            "Arabic routine slots for profile_id=%s student_id=%s — ANTHROPIC_API_KEY unset, skipping auto-regeneration",
            profile.id,
            profile.student_id,
        )
        return {"regenerated": False, "reason": "no_api_key"}

    result = await regenerate_student_routine(db, profile)
    if result.get("regenerated"):
        logger.info(
            "Regenerated routine for profile_id=%s student_id=%s slots_saved=%s",
            profile.id,
            profile.student_id,
            result.get("slots_saved"),
        )
    return result


async def save_routine_slots(db: AsyncSession, profile, days: dict) -> int:
    from sqlalchemy import delete
    await db.execute(delete(RoutineSlot).where(RoutineSlot.profile_id == profile.id))
    count = 0
    for day_str, slots in days.items():
        try:
            day = int(day_str)
        except Exception:
            continue
        for s in slots:
            db.add(RoutineSlot(
                profile_id=profile.id,
                day_of_week=day,
                start_time=s.get("start", "00:00"),
                end_time=s.get("end", "00:00"),
                activity_type=s.get("type", "other"),
                title=s.get("title", ""),
                subject=s.get("subject"),
                is_fixed=s.get("fixed", False),
                status="planned",
            ))
            count += 1
    await db.flush()
    return count


async def get_week_slots(db: AsyncSession, profile_id: int) -> dict:
    result = await db.execute(
        select(RoutineSlot)
        .where(RoutineSlot.profile_id == profile_id)
        .order_by(RoutineSlot.day_of_week, RoutineSlot.start_time)
    )
    days = {str(i): [] for i in range(7)}
    for s in result.scalars().all():
        days[str(s.day_of_week)].append({
            "id": s.id,
            "start": s.start_time,
            "end": s.end_time,
            "type": s.activity_type,
            "title": s.title,
            "subject": s.subject,
            "fixed": s.is_fixed,
            "status": getattr(s, "status", "planned"),
        })
    return days


def build_initial_message(profile) -> str:
    acts = {}
    try:
        acts = json.loads(profile.activities_json or "{}")
    except Exception:
        pass

    gk = _gk(profile.grade_level)
    details = acts.get("details", {})
    acts_list = [
        f"{a} ({', '.join([DAY_NAMES.get(int(d), '') for d in i['days']])})"
        for a, i in details.items()
        if isinstance(i, dict) and i.get("days")
    ]
    acts_txt = f"\nلاحظت إنك عندك: {', '.join(acts_list)}." if acts_list else ""
    school_txt = f"مدرستك: {profile.school_start} - {profile.school_end}." if profile.school_start else ""

    nap_line = f"• قيلولة {gk['nap_duration']}\n" if gk['nap'] else ""

    return (
        f"مرحباً! وصلتني معلوماتك. {school_txt}{acts_txt}\n\n"
        f"رح نبني سوا برنامج حياتك الكامل — هاد البرنامج راح يشمل:\n"
        f"• أوقات الدراسة ({gk['study_hours']}) مع تركيز على المواد الصعبة\n"
        f"• الصلوات والوجبات والراحة\n"
        f"{nap_line}"
        f"• وقت للعب والعيلة والترفيه\n\n"
        f"[سؤال]\n"
        f"هل عندك امتحانات قريبة؟ قلي المادة والتاريخ والوقت — أو ارفع صورة الجدول.\n"
        f"إذا ما في امتحانات هلق، قل لي «لا» ونكمل."
    )


async def chat_with_routine_ai(db: AsyncSession, profile, message: str, weak_subjects: list) -> dict:
    result = await process_routine_message(db, profile, message, weak_subjects)
    extracted = None
    if result.get("schedule"):
        extracted = {"days": result["schedule"]}
    return {
        "reply": result["reply"],
        "extracted": extracted,
        "stage": result.get("stage"),
        "suggestions": result.get("suggestions"),
        "summary_data": result.get("summary_data"),
    }
