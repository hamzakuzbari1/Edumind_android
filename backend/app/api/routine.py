"""Daily routine API — حياتي."""
import json

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_student_actor
from app.db.session import get_db
from app.models.routine import RoutineSlot, StudentRoutineProfile
from app.models.user import User
from app.services.routine_service import (
    acknowledge_saved_exams,
    build_initial_message,
    chat_with_routine_ai,
    finalize_routine_schedule,
    get_or_create_routine_profile,
    get_weak_subjects,
    get_week_slots,
    regenerate_student_routine,
    save_routine_slots,
    start_edit_day,
    week_schedule_contains_arabic,
    _save_exams,
    _validate_slots,
    _review_schedule_claude,
)

router = APIRouter(prefix="/student/routine", tags=["Daily Routine"])


class OnboardingRequest(BaseModel):
    grade_level: str
    school_start: str = "07:30"
    school_end: str = "13:00"
    wake_time: str = "06:30"
    sleep_time: str = "22:00"
    school_days: list[int] = [0, 1, 2, 3, 4]
    activities: dict = {}
    weak_subjects: list[str] = []


class SettingsRequest(BaseModel):
    grade_level: str
    school_start: str = "07:30"
    school_end: str = "13:00"
    wake_time: str = "06:30"
    sleep_time: str = "22:00"
    school_days: list[int] = [0, 1, 2, 3, 4]
    activities: dict = {}
    weak_subjects: list[str] = []


class ExamSaveRequest(BaseModel):
    exams: list[dict]


class ChatRequest(BaseModel):
    message: str


class ConfirmRequest(BaseModel):
    days: dict


class ConfirmSummaryRequest(BaseModel):
    days: dict[str, str] = {}


class EditDayRequest(BaseModel):
    day: int


@router.post("/onboarding")
async def save_onboarding(
    body: OnboardingRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    profile = await get_or_create_routine_profile(db, student.id)
    profile.grade_level = body.grade_level
    profile.school_start = body.school_start
    profile.school_end = body.school_end
    profile.wake_time = body.wake_time
    profile.sleep_time = body.sleep_time
    profile.school_days_json = json.dumps(body.school_days)
    profile.activities_json = json.dumps(body.activities, ensure_ascii=False)
    profile.chat_history_json = "[]"
    profile.chat_stage = "exams"
    profile.day_data_json = "{}"

    # Save weak subjects to planner profile (creates one if not exists)
    if body.weak_subjects:
        from app.models.planner import PlannerProfile
        pp_result = await db.execute(select(PlannerProfile).where(PlannerProfile.student_id == student.id))
        pp = pp_result.scalar_one_or_none()
        if pp:
            pp.weak_subjects_json = json.dumps(body.weak_subjects, ensure_ascii=False)
        else:
            db.add(PlannerProfile(
                student_id=student.id,
                preferred_period="morning",
                school_start=body.school_start,
                school_end=body.school_end,
                max_daily_minutes=180,
                weak_subjects_json=json.dumps(body.weak_subjects, ensure_ascii=False),
                memory_json="{}",
            ))

    await db.commit()
    initial_msg = build_initial_message(profile)
    return {"ok": True, "next": "chat", "initial_message": initial_msg}


@router.patch("/profile")
async def update_settings(
    body: SettingsRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    """تحديث إعدادات البرنامج بدون مسح السجل أو البيانات."""
    profile = await get_or_create_routine_profile(db, student.id)
    profile.grade_level = body.grade_level
    profile.school_start = body.school_start
    profile.school_end = body.school_end
    profile.wake_time = body.wake_time
    profile.sleep_time = body.sleep_time
    profile.school_days_json = json.dumps(body.school_days)
    profile.activities_json = json.dumps(body.activities, ensure_ascii=False)
    if body.weak_subjects:
        from app.models.planner import PlannerProfile
        pp_result = await db.execute(select(PlannerProfile).where(PlannerProfile.student_id == student.id))
        pp = pp_result.scalar_one_or_none()
        if pp:
            pp.weak_subjects_json = json.dumps(body.weak_subjects, ensure_ascii=False)
    await db.commit()
    return {"ok": True}


@router.delete("/profile")
async def reset_profile(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    """حذف البرنامج والبدء من جديد — يمسح السجل والجدول فقط."""
    from sqlalchemy import delete
    profile = await get_or_create_routine_profile(db, student.id)
    await db.execute(delete(RoutineSlot).where(RoutineSlot.profile_id == profile.id))
    profile.chat_history_json = "[]"
    profile.chat_stage = "exams"
    profile.day_data_json = "{}"
    profile.onboarding_complete = False
    await db.commit()
    return {"ok": True}


@router.get("/profile")
async def get_profile(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    profile = await get_or_create_routine_profile(db, student.id)
    from sqlalchemy import func
    from app.models.routine import RoutineSlot
    slot_count_result = await db.execute(
        select(func.count(RoutineSlot.id)).where(RoutineSlot.profile_id == profile.id)
    )
    slot_count = slot_count_result.scalar_one_or_none() or 0
    return {
        "grade_level": profile.grade_level,
        "school_start": profile.school_start,
        "school_end": profile.school_end,
        "wake_time": profile.wake_time,
        "sleep_time": profile.sleep_time,
        "school_days": json.loads(profile.school_days_json or "[0,1,2,3,4]"),
        "activities": json.loads(profile.activities_json or "{}"),
        "onboarding_complete": profile.onboarding_complete,
        "has_schedule": slot_count > 0,
        "chat_stage": profile.chat_stage,
    }


@router.post("/chat")
async def routine_chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    profile = await get_or_create_routine_profile(db, student.id)
    weak = await get_weak_subjects(db, student.id)

    msg = body.message.strip()
    result = await chat_with_routine_ai(db, profile, msg, weak)

    # انتقال تلقائي: إذا قال لا امتحانات، حقن سؤال الأحد
    no_exam_signals = ["لا يوجد", "لا توجد", "ما عندي", "مافي", "لا", "no", "لا امتحانات", "حاليا لا", "لا شي"]
    history = json.loads(profile.chat_history_json or "[]")
    msg_count = len([m for m in history if m.get("role") == "user"])
    is_early = msg_count <= 3
    is_no_exam = any(s in msg.lower() for s in no_exam_signals)

    if is_early and is_no_exam and "?" not in result["reply"] and "يوم" not in result["reply"]:
        day_question = f"تمام! يلا نبني اسبوعك.\n\nيوم الاحد — مدرستك تنتهي {profile.school_end}. قديه توصل البيت؟ وشو بتعمل بعدها بالتفصيل؟"
        result["reply"] = day_question
        history.append({"role": "assistant", "content": day_question})
        profile.chat_history_json = json.dumps(history[-20:], ensure_ascii=False)

    await db.commit()

    schedule = None
    if result.get("extracted") and "days" in result["extracted"]:
        schedule = result["extracted"]["days"]
        errors = _validate_slots(schedule)
        if errors:
            result["reply"] += f"\n\n⚠️ لاحظت تعارضاً في الأوقات: {', '.join(errors[:2])}"
            schedule = None

    return {
        "reply": result["reply"],
        "schedule": schedule,
        "stage": result.get("stage"),
        "suggestions": result.get("suggestions"),
        "summary_data": result.get("summary_data"),
        "ready_to_confirm": schedule is not None,
    }


@router.post("/edit-day")
async def edit_day(
    body: EditDayRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    """الرجوع لتعديل يوم محدد من الأسبوع — المساعد يسأل عنه من جديد دون فقدان بيانات بقية الأيام."""
    if body.day < 0 or body.day > 6:
        raise HTTPException(400, detail="رقم يوم غير صالح.")

    profile = await get_or_create_routine_profile(db, student.id)
    result = await start_edit_day(db, profile, body.day)
    await db.commit()
    return {"reply": result["reply"], "stage": result["stage"]}


@router.post("/confirm-summary")
async def confirm_summary(
    body: ConfirmSummaryRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
    accept_language: str = Header("ar", alias="Accept-Language"),
):
    """تأكيد بطاقة مراجعة المعلومات (مع تعديلات الأيام إن وُجدت) وبناء الجدول مباشرة."""
    profile = await get_or_create_routine_profile(db, student.id)
    if profile.chat_stage != "confirm":
        raise HTTPException(400, detail="البرنامج ليس في مرحلة التأكيد حالياً.")

    try:
        day_data = json.loads(profile.day_data_json or "{}")
    except Exception:
        day_data = {}

    for key, text in body.days.items():
        if key in day_data and isinstance(text, str) and text.strip():
            day_data[key] = text.strip()
    profile.day_data_json = json.dumps(day_data, ensure_ascii=False)
    await db.flush()

    weak = await get_weak_subjects(db, student.id)
    lang = "en" if accept_language.startswith("en") else "ar"
    result = await finalize_routine_schedule(db, profile, day_data, weak, lang=lang)
    await db.commit()

    return {
        "ok": result.get("schedule") is not None,
        "reply": result["reply"],
        "schedule": result.get("schedule"),
        "stage": result.get("stage"),
    }


@router.post("/confirm")
async def confirm_schedule(
    body: ConfirmRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    errors = _validate_slots(body.days)
    if errors:
        raise HTTPException(400, detail=f"تعارض في الأوقات: {errors[0]}")

    profile = await get_or_create_routine_profile(db, student.id)
    count = await save_routine_slots(db, profile, body.days)
    profile.onboarding_complete = True
    await db.commit()
    return {"ok": True, "slots_saved": count}


@router.get("/week")
async def get_week(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    """Read-only weekly schedule — no AI regeneration on load."""
    profile = await get_or_create_routine_profile(db, student.id)
    days = await get_week_slots(db, profile.id)
    return {
        "days": days,
        "onboarding_complete": profile.onboarding_complete,
        "grade_level": profile.grade_level,
    }


@router.post("/regenerate")
async def regenerate_schedule(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
    accept_language: str = Header("ar", alias="Accept-Language"),
):
    """إعادة بناء البرنامج الأسبوعي باستخدام بيانات اليوم المحفوظة."""
    profile = await get_or_create_routine_profile(db, student.id)
    days = await get_week_slots(db, profile.id)
    if not any(isinstance(slots, list) and slots for slots in days.values()):
        raise HTTPException(400, detail="لا يوجد برنامج لإعادة توليده.")

    had_arabic = week_schedule_contains_arabic(days)
    weak = await get_weak_subjects(db, student.id)
    lang = "en" if accept_language.startswith("en") else "ar"
    result = await regenerate_student_routine(db, profile, weak, lang=lang)
    await db.commit()

    if not result.get("regenerated"):
        reason = result.get("reason", "unknown")
        detail = {
            "generation_failed": "تعذر توليد برنامج جديد. حاول لاحقاً.",
            "validation_failed": "البرنامج المُولَّد فيه تعارضات زمنية. حاول مرة أخرى.",
            "no_api_key": "خدمة الذكاء الاصطناعي غير مهيّأة.",
        }.get(reason, "فشلت إعادة التوليد.")
        raise HTTPException(503, detail=detail)

    days = await get_week_slots(db, profile.id)
    return {
        "ok": True,
        "regenerated": True,
        "slots_saved": result["slots_saved"],
        "days": days,
        "had_arabic": had_arabic,
    }


async def _get_owned_slot(db: AsyncSession, slot_id: int, student_id: int):
    result = await db.execute(
        select(RoutineSlot)
        .join(RoutineSlot.profile)
        .where(RoutineSlot.id == slot_id, StudentRoutineProfile.student_id == student_id)
    )
    return result.scalar_one_or_none()


@router.post("/slots/{slot_id}/complete")
async def complete_slot(
    slot_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    slot = await _get_owned_slot(db, slot_id, student.id)
    if not slot:
        raise HTTPException(404, detail="الجلسة غير موجودة")
    slot.status = "completed"
    await db.commit()
    return {"ok": True, "status": "completed"}


@router.post("/slots/{slot_id}/miss")
async def miss_slot(
    slot_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    slot = await _get_owned_slot(db, slot_id, student.id)
    if not slot:
        raise HTTPException(404, detail="الجلسة غير موجودة")
    slot.status = "missed"
    await db.commit()
    return {"ok": True, "status": "missed"}


@router.post("/slots/{slot_id}/undo")
async def undo_slot(
    slot_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    slot = await _get_owned_slot(db, slot_id, student.id)
    if not slot:
        raise HTTPException(404, detail="الجلسة غير موجودة")
    slot.status = "planned"
    await db.commit()
    return {"ok": True, "status": "planned"}


@router.post("/upload-exam")
async def upload_exam_schedule(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    """رفع صورة/PDF برنامج الامتحانات — Mistral OCR ثم تحويل النص إلى JSON."""
    import re
    import json as _json

    from app.core.config import get_settings
    from app.services import mistral_ocr_service, routine_exam_json_service

    settings = get_settings()
    if not settings.MISTRAL_API_KEY:
        raise HTTPException(503, detail="خدمة OCR غير متاحة حالياً.")
    from app.services.claude_service import is_claude_configured

    if not is_claude_configured():
        raise HTTPException(503, detail="خدمة الذكاء الاصطناعي غير متاحة حالياً.")

    data = await file.read()
    mime = file.content_type or "image/jpeg"

    is_pdf = mime == "application/pdf" or (file.filename or "").lower().endswith(".pdf")
    if is_pdf:
        mime = "application/pdf"
        if len(data) > settings.MAX_PDF_BYTES:
            raise HTTPException(status_code=400, detail="حجم ملف PDF كبير جداً")

    today = __import__("datetime").date.today().isoformat()

    try:
        ocr_text = mistral_ocr_service.extract_document_bytes(data, mime)
        ai_text = routine_exam_json_service.structure_exam_schedule_json_from_text(ocr_text, today)
    except Exception as e:
        raise HTTPException(500, detail=f"خطأ في معالجة الملف: {repr(e)[:100]}")

    # استخرج JSON (أزل أي تنسيق markdown محتمل مثل ```json قبل البحث)
    cleaned = ai_text.replace("```json", "").replace("```", "")
    match = re.search(r'\[[\s\S]*\]', cleaned)
    exams = []
    if match:
        try:
            exams = _json.loads(match.group())
        except Exception:
            pass

    return {"ok": True, "exams": exams}


@router.post("/save-exams")
async def save_confirmed_exams(
    body: ExamSaveRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    """حفظ الامتحانات بعد تأكيد الطالب، مع متابعة المحادثة بشكل صحيح بدل تجاهل ما حُفظ."""
    profile = await get_or_create_routine_profile(db, student.id)
    saved = await _save_exams(db, profile, body.exams)
    ack = await acknowledge_saved_exams(profile, body.exams[:saved] if saved else [])
    await db.commit()
    return {"ok": True, "saved": saved, "reply": ack["reply"], "stage": ack["stage"], "exams": ack["exams"]}


@router.post("/review")
async def review_schedule(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    """مراجعة البرنامج المبني — المرحلة الخامسة (AI يقترح تحسينات)."""
    profile = await get_or_create_routine_profile(db, student.id)
    weak = await get_weak_subjects(db, student.id)
    review = await _review_schedule_claude(profile, weak)
    return {
        "ok": True,
        "text": review.get("text", ""),
        "suggestions": review.get("suggestions", []),
    }


@router.post("/renew-week")
async def renew_week(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
    accept_language: str = Header("ar", alias="Accept-Language"),
):
    """تجديد البرنامج الأسبوعي — يستخدم بيانات الأسبوع المحفوظة + الامتحانات + المواد الضعيفة."""
    profile = await get_or_create_routine_profile(db, student.id)
    weak = await get_weak_subjects(db, student.id)
    lang = "en" if accept_language.startswith("en") else "ar"
    result = await regenerate_student_routine(db, profile, weak, lang=lang)

    if result.get("regenerated"):
        await db.commit()
        return {
            "ok": True,
            "reply": "تم تجديد برنامجك الأسبوعي بناءً على امتحاناتك القادمة ومواد الضعف. ✅",
            "renewed": True,
            "slots_saved": result.get("slots_saved", 0),
        }

    return {"ok": True, "reply": "لم أتمكن من تجديد البرنامج الآن. حاول مرة أخرى.", "renewed": False}
