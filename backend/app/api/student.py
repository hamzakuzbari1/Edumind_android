import json
import random
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.deps import AuthContext, get_auth_context, require_student_actor
from app.db.session import get_db
from app.models.chat import ChatMessage
from app.models.catalog import Course, TeacherProfile
from app.models.lesson import Lesson, LessonStatus
from app.models.profile import StudentProfile
from app.models.quiz import QuizAttempt, QuizQuestion
from app.models.user import User, UserRole
from app.schemas.student_parent import StudentLinkedParentsOut
from app.schemas.student import (
    ChatRequest,
    ChatResponse,
    LessonAssetOut,
    LessonCardOut,
    LessonDetailOut,
    ProfileOut,
    ProfileUpdate,
    QuizQuestionOut,
    QuizSubmitRequest,
    QuizSubmitResponse,
    RemedialQuizRequest,
)
from app.services.ai_service import generate_tutor_reply, is_real_reply
from app.services.chat_visual_service import decide_chat_visual
from app.services.lesson_curated_insights_service import resolve_lesson_insights
from app.services.quiz_service import (
    QUIZ_FOCUS_HINTS,
    generate_quiz_questions,
    generate_remedial_questions,
    is_lesson_text_too_short,
)
from app.services.rag_service import retrieve_chunk_records
from app.services.chat_audio_service import schedule_chat_answer_audio
from app.services.student_chat_stt_service import transcribe_student_chat_audio
from app.services.activity_service import (
    log_quiz_submitted,
    log_weak_subject_alert,
    log_performance_improved,
)
from app.services.student_courses_service import student_has_lesson_access
from app.services.lesson_assets_service import assets_public_urls, sync_lesson_legacy_columns
from app.services.lesson_capabilities import build_lesson_capabilities
from app.utils.media_urls import public_upload_url
from app.services.planner_memory_service import get_or_create_profile

router = APIRouter(prefix="/student", tags=["Student"])
settings = get_settings()
SOURCE_MARKER = "\n\n[[EDUSPARK_SOURCES:"
SOURCE_MARKER_END = "]]"
AUDIO_MARKER = "\n\n[[EDUSPARK_AUDIO:"
AUDIO_MARKER_END = "]]"
VISUAL_MARKER = "\n\n[[EDUSPARK_VISUAL:"
VISUAL_MARKER_END = "]]"


def _public_upload_url(path: str | None) -> str | None:
    if not path:
        return None
    try:
        rel = Path(path).resolve().relative_to(Path(settings.UPLOAD_DIR).resolve())
        return "/uploads/" + "/".join(rel.parts)
    except Exception:
        return None


def _format_time(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.strftime("%H:%M")


def _pack_ai_content(
    reply: str,
    sources: list[dict],
    audio_url: str | None = None,
    visual: dict | None = None,
) -> str:
    content = reply
    if sources:
        payload = json.dumps(sources, ensure_ascii=False)
        content = f"{content}{SOURCE_MARKER}{payload}{SOURCE_MARKER_END}"
    if audio_url:
        payload = json.dumps({"audioUrl": audio_url}, ensure_ascii=False)
        content = f"{content}{AUDIO_MARKER}{payload}{AUDIO_MARKER_END}"
    if visual:
        payload = json.dumps(visual, ensure_ascii=False)
        content = f"{content}{VISUAL_MARKER}{payload}{VISUAL_MARKER_END}"
    return content


def _split_ai_content(content: str) -> tuple[str, list[dict], str | None, dict | None]:
    audio_url = None
    visual: dict | None = None

    if VISUAL_MARKER in content:
        text, _, tail = content.partition(VISUAL_MARKER)
        visual_json, end, rest = tail.partition(VISUAL_MARKER_END)
        if end:
            content = f"{text}{rest}".strip()
            try:
                parsed = json.loads(visual_json)
                if isinstance(parsed, dict):
                    visual = parsed
            except Exception:
                visual = None

    if AUDIO_MARKER in content:
        text, _, tail = content.partition(AUDIO_MARKER)
        audio_json, end, rest = tail.partition(AUDIO_MARKER_END)
        if end:
            content = f"{text}{rest}".strip()
            try:
                audio_payload = json.loads(audio_json)
                if isinstance(audio_payload, dict):
                    audio_url = audio_payload.get("audioUrl")
            except Exception:
                audio_url = None

    if SOURCE_MARKER not in content:
        return content, [], audio_url, visual
    text, _, tail = content.partition(SOURCE_MARKER)
    source_json, end, _ = tail.rpartition(SOURCE_MARKER_END)
    if not end:
        return content, [], audio_url, visual
    try:
        sources = json.loads(source_json)
    except Exception:
        return text.strip(), [], audio_url, visual
    return text.strip(), sources if isinstance(sources, list) else [], audio_url, visual


def _chunk_sources(chunks) -> list[dict]:
    sources = []
    seen_pages = set()
    for chunk in chunks[:3]:
        meta = {}
        if chunk.metadata_json:
            try:
                meta = json.loads(chunk.metadata_json)
            except Exception:
                meta = {}
        page_hint = meta.get("page_hint") if isinstance(meta, dict) else None
        page = page_hint.get("page") if isinstance(page_hint, dict) else None
        source = meta.get("source") if isinstance(meta, dict) else None
        segment = meta.get("segment") if isinstance(meta, dict) else None
        dedupe_key = page or chunk.chunk_index
        if dedupe_key in seen_pages:
            continue
        seen_pages.add(dedupe_key)
        snippet = " ".join((chunk.content or "").split())[:180]
        label = (
            f"مقطع فيديو {segment or chunk.chunk_index + 1}"
            if source == "video"
            else (f"صفحة {page}" if page else f"فقرة {chunk.chunk_index + 1}")
        )
        sources.append(
            {
                "label": label,
                "page": page,
                "snippet": snippet,
            }
        )
        if len(sources) >= 2:
            break
    return sources


def _message_out(message: ChatMessage, audio_by_id: dict[int, str] | None = None) -> dict:
    text, sources, stored_audio_url, visual = (
        _split_ai_content(message.content) if message.role == "ai" else (message.content, [], None, None)
    )
    out = {
        "id": message.id,
        "role": message.role,
        "text": text,
        "time": _format_time(message.created_at),
    }
    if sources:
        out["sources"] = sources
    audio_url = (audio_by_id or {}).get(message.id) or stored_audio_url
    if audio_url:
        out["audioUrl"] = audio_url
    if visual:
        out["visualElement"] = visual
    return out


def _quiz_question_out(question: QuizQuestion) -> dict:
    return {
        "id": question.id,
        "question": question.question,
        "options": json.loads(question.options_json),
        "correctIndex": question.correct_index,
        "hint": question.hint,
    }


def _generated_quiz_question_out(question: dict, prefix: str, index: int) -> dict:
    return {
        "id": f"{prefix}-{index}",
        "question": question["question"],
        "options": question["options"],
        "correctIndex": question["correct_index"],
        "hint": question.get("hint"),
    }


async def _lesson_for_chat(db: AsyncSession, lesson_id: int) -> Lesson:
    result = await db.execute(
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(selectinload(Lesson.chunks), selectinload(Lesson.assets))
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")
    caps = await build_lesson_capabilities(db, lesson)
    if caps["ai_processing"]:
        raise HTTPException(status_code=409, detail="جاري تحضير المعلم الذكي — حاول بعد قليل")
    if caps["ai_error"]:
        raise HTTPException(status_code=503, detail=lesson.error_message or "فشلت معالجة الدرس")
    if not caps["has_ai_chat"]:
        raise HTTPException(status_code=409, detail="المعلم الذكي غير جاهز بعد — انتظر اكتمال معالجة محتوى الدرس")
    return lesson


async def _lesson_voice_tts_status(db: AsyncSession, lesson: Lesson) -> tuple[bool, str | None]:
    from app.services.teacher_voice_service import get_ready_tts_reference_for_teacher

    if not settings.ENABLE_TTS:
        return False, "تشغيل الصوت معطّل على هذا الخادم."

    voice_ref = await get_ready_tts_reference_for_teacher(db, lesson.teacher_id)
    voice_id = (voice_ref.get("elevenlabs_voice_id") or settings.ELEVENLABS_DEFAULT_VOICE_ID or "").strip()
    if not voice_id:
        return False, "لا توجد عيّنة صوت جاهزة للمعلّم لهذا الدرس."
    if not (settings.ELEVENLABS_API_KEY or "").strip():
        return False, "مفتاح ElevenLabs غير مضبوط على الخادم."
    return True, None


async def _run_chat_turn(
    *,
    db: AsyncSession,
    lesson: Lesson,
    student: User,
    message_text: str,
) -> ChatResponse:
    profile_result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == student.id)
    )
    profile = profile_result.scalar_one_or_none()
    difficulty = profile.difficulty if profile else "medium"
    student_age = profile.age if profile else None
    academic_interests = json.loads(profile.interests_json or "[]") if profile else []
    personal_hobbies = json.loads(profile.hobbies_json or "[]") if profile else []
    learning_style = profile.learning_style if profile else "theoretical"
    future_goal = profile.future_goal if profile else "undecided"
    preferred_explanation_style = (
        profile.preferred_explanation_style if profile else None
    )
    personality_mode = profile.personality_mode if profile else "friendly_teacher"

    teacher_profile_result = await db.execute(
        select(TeacherProfile).where(TeacherProfile.user_id == lesson.teacher_id)
    )
    teacher_profile = teacher_profile_result.scalar_one_or_none()
    from app.services.teacher_ai_profile_service import teacher_chat_kwargs

    teacher_kwargs = teacher_chat_kwargs(teacher_profile)

    from app.services.student_learning_profile_service import (
        get_learning_context_for_chat,
        learning_chat_kwargs,
        record_chat_interaction,
    )

    learning_ctx = await get_learning_context_for_chat(db, student.id, lesson=lesson)
    memory_kwargs = learning_chat_kwargs(learning_ctx)

    db.add(
        ChatMessage(
            lesson_id=lesson.id,
            student_id=student.id,
            role="student",
            content=message_text,
        )
    )

    chunk_records = await retrieve_chunk_records(db, lesson.id, message_text)
    chunks = [chunk.content for chunk in chunk_records]
    sources = _chunk_sources(chunk_records)
    reply = await generate_tutor_reply(
        message_text,
        chunks,
        lesson.persona_prompt or "",
        lesson.subject,
        lesson.grade,
        difficulty,
        student_age=student_age,
        academic_interests=academic_interests,
        personal_hobbies=personal_hobbies,
        learning_style=learning_style,
        future_goal=future_goal,
        preferred_explanation_style=preferred_explanation_style,
        personality_mode=personality_mode,
        **teacher_kwargs,
        **memory_kwargs,
    )

    await record_chat_interaction(db, student.id, lesson, message_text)

    visual = None
    if is_real_reply(reply):
        context_chunks = "\n\n---\n\n".join(chunks)
        visual = await decide_chat_visual(message_text, reply, context_chunks=context_chunks)

    ai_msg = ChatMessage(
        lesson_id=lesson.id,
        student_id=student.id,
        role="ai",
        content=_pack_ai_content(reply, sources, visual=visual),
    )
    db.add(ai_msg)
    await db.commit()
    await db.refresh(ai_msg)

    from app.services.teacher_voice_service import get_ready_tts_reference_for_teacher

    voice_ref = await get_ready_tts_reference_for_teacher(db, lesson.teacher_id)
    speaker_wav = lesson.voice_path or voice_ref.get("speaker_wav")
    elevenlabs_voice_id = voice_ref.get("elevenlabs_voice_id") or settings.ELEVENLABS_DEFAULT_VOICE_ID
    voice_tts_available, voice_tts_message = await _lesson_voice_tts_status(db, lesson)
    if voice_tts_available:
        schedule_chat_answer_audio(
            ai_message_id=ai_msg.id,
            reply=reply,
            sources=sources,
            speaker_wav=speaker_wav,
            elevenlabs_voice_id=elevenlabs_voice_id,
            lesson_id=lesson.id,
            visual=visual,
        )

    history = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.lesson_id == lesson.id, ChatMessage.student_id == student.id)
        .order_by(ChatMessage.created_at, ChatMessage.id)
    )
    messages = [_message_out(m) for m in history.scalars().all()]

    return ChatResponse(
        reply=reply,
        messages=messages,
        question=message_text,
        audio_url=None,
        sources=sources,
        voiceTtsAvailable=voice_tts_available,
        voiceTtsMessage=voice_tts_message,
    )


@router.get("/lessons", response_model=list[LessonCardOut])
async def list_lessons(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    from app.models.enrollment import PaymentStatus, StudentCourseAccess

    paid_course_ids = await db.execute(
        select(StudentCourseAccess.course_id).where(
            StudentCourseAccess.student_id == student.id,
            StudentCourseAccess.payment_status == PaymentStatus.paid,
        )
    )
    course_ids = list(paid_course_ids.scalars().all())
    if not course_ids:
        return []

    result = await db.execute(
        select(Lesson)
        .where(
            Lesson.status == LessonStatus.processed,
            Lesson.course_id.in_(course_ids),
        )
        .options(selectinload(Lesson.teacher))
        .order_by(Lesson.created_at.desc())
    )
    lessons = result.scalars().all()
    return [
        LessonCardOut(
            id=l.id,
            title=l.title,
            subject=l.subject,
            grade=l.grade,
            teacherName=l.teacher.name if l.teacher else "معلم",
            preview=l.preview or "درس تفاعلي بالذكاء الاصطناعي",
            pdfUrl=_public_upload_url(l.pdf_path),
        )
        for l in lessons
    ]


@router.get("/lesson/{lesson_id}", response_model=LessonDetailOut)
async def get_lesson(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
    student: User = Depends(require_student_actor()),
):
    result = await db.execute(
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(
            selectinload(Lesson.teacher),
            selectinload(Lesson.course).selectinload(Course.teacher_profile),
            selectinload(Lesson.quiz_questions),
            selectinload(Lesson.chunks),
            selectinload(Lesson.assets),
        )
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")

    if not await student_has_lesson_access(db, student.id, lesson):
        raise HTTPException(status_code=403, detail="الدورة مقفلة — أكمل الدفع لفتح الدرس")

    sync_lesson_legacy_columns(lesson)
    caps = await build_lesson_capabilities(db, lesson)
    urls = assets_public_urls(lesson)
    asset_list = [
        LessonAssetOut(asset_type=atype, url=url)
        for atype, url in urls.items()
        if url and atype in ("video", "pdf", "homework")
    ]

    chat_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.lesson_id == lesson_id, ChatMessage.student_id == student.id)
        .order_by(ChatMessage.created_at, ChatMessage.id)
    )
    messages = [_message_out(m) for m in chat_result.scalars().all()]

    if caps["has_ai_chat"] and not messages:
        messages = [
            {
                "id": 1,
                "role": "ai",
                "text": f"أهلا {student.name}! أنا معلمك الذكي. اسألني أي شيء عن درس «{lesson.title}».",
                "time": _format_time(datetime.utcnow()),
            }
        ]
    elif caps["ai_processing"] and not messages:
        messages = [
            {
                "id": 1,
                "role": "ai",
                "text": "جاري تحضير المعلم الذكي من محتوى الدرس… سيكون جاهزاً خلال لحظات.",
                "time": _format_time(datetime.utcnow()),
            }
        ]
    elif caps["ai_error"] and not messages:
        messages = [
            {
                "id": 1,
                "role": "ai",
                "text": lesson.error_message or "تعذر تجهيز المعلم الذكي لهذا الدرس.",
                "time": _format_time(datetime.utcnow()),
            }
        ]

    lesson_text = "\n\n".join(
        chunk.content for chunk in sorted(lesson.chunks, key=lambda x: x.chunk_index)
    )
    insights = (
        resolve_lesson_insights(lesson, lesson_text or lesson.preview or "")
        if caps["has_ai_chat"]
        else {"summary": [], "keywords": []}
    )

    quiz = []
    if caps["has_generated_quiz"]:
        for q in sorted(lesson.quiz_questions, key=lambda x: x.sort_order):
            quiz.append(_quiz_question_out(q))

    teacher_name = lesson.teacher.name if lesson.teacher else "معلم"
    teacher_image_url: str | None = None
    if lesson.course and lesson.course.teacher_profile:
        teacher_name = lesson.course.teacher_profile.full_name or teacher_name
        teacher_image_url = public_upload_url(lesson.course.teacher_profile.image_url)

    from app.models.student_activity_tracking import EngagementEventType
    from app.services import student_activity_tracking_service
    from app.services.lesson_completion_service import mark_lesson_started

    await mark_lesson_started(db, student.id, lesson.id)
    await student_activity_tracking_service.record_engagement_event(
        db,
        student.id,
        EngagementEventType.lesson_opened,
        auth_session_id=ctx.session_id,
        resource_type="lesson",
        resource_id=lesson.id,
        metadata={"course_id": lesson.course_id},
    )
    await db.commit()

    voice_tts_available, voice_tts_message = await _lesson_voice_tts_status(db, lesson)

    return LessonDetailOut(
        id=lesson.id,
        courseId=lesson.course_id,
        title=lesson.title,
        subject=lesson.subject,
        grade=lesson.grade,
        teacherName=teacher_name,
        teacherImageUrl=teacher_image_url,
        preview=lesson.preview or "",
        pdfUrl=urls.get("pdf"),
        videoUrl=urls.get("video"),
        assets=asset_list,
        lessonSummary=insights["summary"],
        keywords=insights["keywords"],
        chatMessages=messages,
        quizQuestions=quiz,
        voiceTtsAvailable=voice_tts_available,
        voiceTtsMessage=voice_tts_message,
        **caps,
    )


@router.post("/chat", response_model=ChatResponse)
async def student_chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    lesson = await _lesson_for_chat(db, body.lesson_id)
    return await _run_chat_turn(
        db=db,
        lesson=lesson,
        student=student,
        message_text=body.message,
    )


@router.post("/chat/voice", response_model=ChatResponse)
async def student_voice_chat(
    lesson_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    lesson = await _lesson_for_chat(db, lesson_id)

    data = await file.read()
    if len(data) > settings.MAX_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="حجم الملف الصوتي كبير جدا")

    upload_dir = Path(settings.UPLOAD_DIR) / f"student_{student.id}"
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "question.webm").suffix or ".webm"
    audio_path = upload_dir / f"question_{uuid.uuid4().hex}{ext}"
    audio_path.write_bytes(data)

    question = await transcribe_student_chat_audio(audio_path)
    if not question.strip():
        raise HTTPException(status_code=400, detail="تعذر تحويل الصوت إلى نص")

    return await _run_chat_turn(
        db=db,
        lesson=lesson,
        student=student,
        message_text=question,
    )


@router.delete("/lesson/{lesson_id}/chat", status_code=204)
async def clear_lesson_chat(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    lesson = await _lesson_for_chat(db, lesson_id)
    await db.execute(
        delete(ChatMessage).where(
            ChatMessage.lesson_id == lesson.id,
            ChatMessage.student_id == student.id,
        )
    )
    await db.commit()


@router.get("/quiz/{lesson_id}", response_model=list[QuizQuestionOut])
async def get_quiz(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_student_actor()),
):
    lesson_result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = lesson_result.scalar_one_or_none()
    if lesson and is_lesson_text_too_short(lesson.preview or ""):
        raise HTTPException(status_code=404, detail="نص الدرس قصير جداً لإنشاء اختبار موثوق")

    result = await db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.lesson_id == lesson_id)
        .order_by(QuizQuestion.sort_order)
    )
    questions = result.scalars().all()
    if not questions:
        raise HTTPException(status_code=404, detail="لا يوجد اختبار لهذا الدرس")
    return [
        QuizQuestionOut(
            id=q.id,
            question=q.question,
            options=json.loads(q.options_json),
            hint=q.hint,
        )
        for q in questions
    ]


@router.post("/lesson/{lesson_id}/quiz/regenerate")
async def regenerate_lesson_quiz(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    result = await db.execute(
        select(Lesson)
        .where(Lesson.id == lesson_id, Lesson.status == LessonStatus.processed)
        .options(selectinload(Lesson.chunks))
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")

    lesson_text = "\n\n".join(
        chunk.content for chunk in sorted(lesson.chunks, key=lambda x: x.chunk_index)
    )
    if is_lesson_text_too_short(lesson_text or lesson.preview or ""):
        raise HTTPException(status_code=400, detail="نص الدرس قصير جداً لإنشاء اختبار موثوق")

    old_result = await db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.lesson_id == lesson.id)
        .order_by(QuizQuestion.sort_order)
    )
    old_questions = old_result.scalars().all()
    avoid_questions = [q.question for q in old_questions]
    target_count = max(settings.QUIZ_COUNT, 5)
    minimum_count = min(4, target_count)

    focus_pool = list(QUIZ_FOCUS_HINTS)
    random.shuffle(focus_pool)
    quiz_items: list[dict] = []
    for focus in focus_pool[:3]:
        generated = await generate_quiz_questions(
            lesson_text or lesson.preview or "",
            lesson.subject,
            lesson.grade,
            count=target_count,
            avoid_questions=avoid_questions,
            focus_hint=focus,
        )
        if len(generated) > len(quiz_items):
            quiz_items = generated
        if len(quiz_items) >= target_count:
            break

    if len(quiz_items) < minimum_count:
        generated = await generate_quiz_questions(
            lesson_text or lesson.preview or "",
            lesson.subject,
            lesson.grade,
            count=target_count,
            focus_hint=random.choice(focus_pool or list(QUIZ_FOCUS_HINTS)),
        )
        if len(generated) > len(quiz_items):
            quiz_items = generated

    if len(quiz_items) < minimum_count:
        raise HTTPException(
            status_code=400,
            detail=f"تعذر توليد اختبار متنوع من {minimum_count} أسئلة موثوقة من نص الدرس",
        )

    await db.execute(delete(QuizAttempt).where(QuizAttempt.lesson_id == lesson.id))
    await db.execute(delete(QuizQuestion).where(QuizQuestion.lesson_id == lesson.id))
    new_questions: list[QuizQuestion] = []
    for i, q in enumerate(quiz_items):
        question = QuizQuestion(
            lesson_id=lesson.id,
            question=q["question"],
            options_json=json.dumps(q["options"], ensure_ascii=False),
            correct_index=q["correct_index"],
            hint=q.get("hint"),
            sort_order=i,
        )
        db.add(question)
        new_questions.append(question)

    await db.commit()
    for question in new_questions:
        await db.refresh(question)

    return {"quizQuestions": [_quiz_question_out(q) for q in new_questions]}


@router.post("/lesson/{lesson_id}/quiz/remedial")
async def generate_lesson_remedial_quiz(
    lesson_id: int,
    body: RemedialQuizRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    result = await db.execute(
        select(Lesson)
        .where(Lesson.id == lesson_id, Lesson.status == LessonStatus.processed)
        .options(selectinload(Lesson.chunks))
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")

    question_result = await db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.lesson_id == lesson.id)
        .order_by(QuizQuestion.sort_order)
    )
    questions = question_result.scalars().all()
    mistakes = []
    for question in questions:
        selected = body.answers.get(str(question.id), body.answers.get(question.id, -1))
        try:
            selected_index = int(selected)
        except Exception:
            selected_index = -1
        if selected_index == question.correct_index:
            continue
        options = json.loads(question.options_json)
        mistakes.append(
            {
                "question": question.question,
                "selected": options[selected_index] if 0 <= selected_index < len(options) else "بدون إجابة",
                "correct": options[question.correct_index],
                "hint": question.hint,
            }
        )

    if not mistakes:
        raise HTTPException(status_code=400, detail="لا توجد أخطاء تحتاج أسئلة علاجية")

    lesson_text = "\n\n".join(
        chunk.content for chunk in sorted(lesson.chunks, key=lambda x: x.chunk_index)
    )
    remedial_items = await generate_remedial_questions(
        lesson_text or lesson.preview or "",
        lesson.subject,
        lesson.grade,
        mistakes,
    )
    if not remedial_items:
        raise HTTPException(status_code=400, detail="تعذر توليد أسئلة علاجية من نص الدرس")

    return {
        "questions": [
            _generated_quiz_question_out(item, f"remedial-{lesson.id}", idx)
            for idx, item in enumerate(remedial_items)
        ]
    }


@router.post("/quiz/submit", response_model=QuizSubmitResponse)
async def submit_quiz(
    body: QuizSubmitRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    lesson_id = body.lesson_id
    result = await db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.lesson_id == lesson_id)
        .order_by(QuizQuestion.sort_order)
    )
    questions = result.scalars().all()
    if not questions:
        raise HTTPException(status_code=404, detail="لا يوجد اختبار")

    correct = 0
    feedback = []
    for q in questions:
        selected = body.answers.get(str(q.id), body.answers.get(q.id, -1))
        is_correct = int(selected) == q.correct_index
        if is_correct:
            correct += 1
        feedback.append(
            {
                "questionId": q.id,
                "correct": is_correct,
                "hint": q.hint if not is_correct else None,
                "message": "إجابة صحيحة!" if is_correct else "حاول مرة أخرى وراجع التلميح",
            }
        )

    total = len(questions)
    score_percent = round((correct / total) * 100) if total else 0

    lesson_result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = lesson_result.scalar_one_or_none()
    subject = lesson.subject if lesson else "الدرس"

    db.add(
        QuizAttempt(
            lesson_id=lesson_id,
            student_id=student.id,
            answers_json=json.dumps(body.answers, ensure_ascii=False),
            correct_count=correct,
            feedback_json=json.dumps(feedback, ensure_ascii=False),
        )
    )
    await db.flush()

    attempt_row = await db.execute(
        select(QuizAttempt)
        .where(QuizAttempt.student_id == student.id, QuizAttempt.lesson_id == lesson_id)
        .order_by(QuizAttempt.id.desc())
        .limit(1)
    )
    attempt = attempt_row.scalar_one()

    child_name = student.name.split()[0] if student.name else "الطالب"
    await log_quiz_submitted(
        db,
        student_id=student.id,
        student_name=child_name,
        subject=subject,
        score_percent=score_percent,
        lesson_id=lesson_id,
    )

    # ربط نتيجة الكويز بالتقويم تلقائياً
    planner_profile = await get_or_create_profile(db, student.id)
    import json as _json
    weak = _json.loads(planner_profile.weak_subjects_json or "[]")
    if not isinstance(weak, list):
        weak = []

    if score_percent < 60:
        # أداء ضعيف — أضف المادة للمواد الضعيفة
        if subject not in weak:
            weak.append(subject)
            planner_profile.weak_subjects_json = _json.dumps(weak, ensure_ascii=False)
            await log_weak_subject_alert(
                db,
                student_id=student.id,
                student_name=child_name,
                subject=subject,
            )
    elif score_percent >= 80 and subject in weak:
        # أداء جيد — أشيل المادة من الضعيفة
        weak.remove(subject)
        planner_profile.weak_subjects_json = _json.dumps(weak, ensure_ascii=False)
        await log_performance_improved(
            db,
            student_id=student.id,
            student_name=child_name,
            subject=subject,
            improvement_percent=score_percent,
        )

    from app.services.integration_hooks import after_lesson_quiz_submitted
    from app.services import lesson_completion_service

    await after_lesson_quiz_submitted(db, student.id, lesson_id, score_percent, attempt.id)
    await lesson_completion_service.on_quiz_submitted_for_lesson(db, student.id, lesson_id)

    if lesson:
        from app.services import student_learning_profile_service

        await student_learning_profile_service.record_quiz_result(
            db, student.id, lesson, questions, body.answers, score_percent
        )

    await db.commit()

    return QuizSubmitResponse(
        correct_count=correct,
        total=total,
        feedback=feedback,
        score_percent=score_percent,
    )


def _profile_out(profile: StudentProfile | None) -> ProfileOut:
    if not profile:
        return ProfileOut(
            interests=[],
            hobbies=[],
            difficulty="medium",
            age=None,
            learning_style="theoretical",
            future_goal="undecided",
            preferred_explanation_style="normal",
            personality_mode="friendly_teacher",
        )
    return ProfileOut(
        interests=json.loads(profile.interests_json or "[]"),
        hobbies=json.loads(profile.hobbies_json or "[]"),
        difficulty=profile.difficulty,
        age=profile.age,
        learning_style=profile.learning_style,
        future_goal=profile.future_goal,
        preferred_explanation_style=profile.preferred_explanation_style,
        personality_mode=profile.personality_mode,
    )


@router.put("/profile", response_model=ProfileOut)
async def update_profile(
    body: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    from app.services.ai_service import VALID_PERSONALITY_MODES

    if body.personality_mode not in VALID_PERSONALITY_MODES:
        raise HTTPException(status_code=400, detail="نمط الشخصية غير مدعوم")

    result = await db.execute(select(StudentProfile).where(StudentProfile.user_id == student.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = StudentProfile(user_id=student.id)
        db.add(profile)

    profile.interests_json = json.dumps(body.interests, ensure_ascii=False)
    profile.hobbies_json = json.dumps(body.hobbies, ensure_ascii=False)
    profile.difficulty = body.difficulty
    profile.age = body.age
    profile.learning_style = body.learning_style
    profile.future_goal = body.future_goal
    profile.preferred_explanation_style = body.preferred_explanation_style
    profile.personality_mode = body.personality_mode
    await db.commit()
    await db.refresh(profile)

    return _profile_out(profile)


@router.get("/linked-parents", response_model=StudentLinkedParentsOut)
async def student_linked_parents(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    from app.services.student_parent_transparency_service import list_linked_parents_for_student

    return await list_linked_parents_for_student(db, student.id)


@router.get("/profile", response_model=ProfileOut)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    result = await db.execute(select(StudentProfile).where(StudentProfile.user_id == student.id))
    profile = result.scalar_one_or_none()
    return _profile_out(profile)
