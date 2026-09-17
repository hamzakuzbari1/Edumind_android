import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import require_role
from app.db.session import get_db
from app.models.lesson import Lesson, LessonStatus
from app.models.quiz import QuizQuestion
from app.models.user import User, UserRole
from app.schemas.teacher import LessonOut, ProcessResponse
from app.services.lesson_processor import process_lesson
from app.services.lesson_processing_tasks import schedule_lesson_processing
from app.services.quiz_service import is_lesson_text_too_short

router = APIRouter(prefix="/teacher", tags=["Teacher"])
settings = get_settings()


def _ensure_upload_dir() -> Path:
    p = Path(settings.UPLOAD_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _public_upload_url(path: str | None) -> str | None:
    if not path:
        return None
    try:
        rel = Path(path).resolve().relative_to(Path(settings.UPLOAD_DIR).resolve())
        return "/uploads/" + "/".join(rel.parts)
    except Exception:
        return None


def _delete_file(path: str | None) -> None:
    if not path:
        return
    try:
        target = Path(path).resolve()
        upload_root = Path(settings.UPLOAD_DIR).resolve()
        if target.is_file() and target.is_relative_to(upload_root):
            target.unlink(missing_ok=True)
    except Exception:
        return


def _delete_lesson_artifacts(lesson: Lesson) -> None:
    _delete_file(lesson.pdf_path)
    _delete_file(lesson.voice_path)
    for pattern_root, pattern in (
        (Path(settings.VECTOR_INDEX_DIR), f"lesson_{lesson.id}.faiss"),
        (Path(settings.TTS_OUTPUT_DIR), f"lesson_{lesson.id}_*.wav"),
    ):
        try:
            root = pattern_root.resolve()
            upload_root = Path(settings.UPLOAD_DIR).resolve()
            if not root.is_relative_to(upload_root):
                continue
            for file_path in root.glob(pattern):
                if file_path.is_file():
                    file_path.unlink(missing_ok=True)
        except Exception:
            continue


@router.post("/upload/pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    subject: str = Form(...),
    grade: str = Form(...),
    title: str | None = Form(None),
    lesson_id: int | None = Form(None),
    course_id: int | None = Form(None),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="يجب أن يكون الملف PDF")

    data = await file.read()
    if len(data) > settings.MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="حجم الملف يتجاوز الحد المسموح")

    upload_dir = _ensure_upload_dir() / f"teacher_{teacher.id}"
    upload_dir.mkdir(parents=True, exist_ok=True)

    if lesson_id:
        result = await db.execute(
            select(Lesson).where(Lesson.id == lesson_id, Lesson.teacher_id == teacher.id)
        )
        lesson = result.scalar_one_or_none()
        if not lesson:
            raise HTTPException(status_code=404, detail="الدرس غير موجود")
    else:
        lesson = Lesson(
            teacher_id=teacher.id,
            course_id=course_id,
            subject=subject,
            grade=grade,
            title=title or "درس جديد",
            status=LessonStatus.draft,
        )
        db.add(lesson)
        await db.flush()

    filename = f"{lesson.id}_{uuid.uuid4().hex}.pdf"
    pdf_path = upload_dir / filename
    pdf_path.write_bytes(data)

    lesson.pdf_path = str(pdf_path)
    lesson.subject = subject
    lesson.grade = grade
    if title:
        lesson.title = title
    if course_id:
        lesson.course_id = course_id
    lesson.status = LessonStatus.draft
    lesson.error_message = None
    await db.commit()
    await db.refresh(lesson)
    schedule_lesson_processing(lesson.id)

    return {
        "lesson_id": lesson.id,
        "filename": file.filename,
        "message": "تم رفع ملف PDF بنجاح",
    }


@router.post("/upload/voice")
async def upload_voice(
    file: UploadFile = File(...),
    lesson_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    """Legacy per-lesson upload — prefer POST /teacher/voice-sample for teacher AI voice."""
    from app.services.teacher_voice_service import upload_voice_sample

    result = await db.execute(
        select(Lesson).where(Lesson.id == lesson_id, Lesson.teacher_id == teacher.id)
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")

    data = await file.read()
    sample_out = await upload_voice_sample(db, teacher, data, file.filename or "voice.webm")

    return {
        "lesson_id": lesson.id,
        "message": "تم رفع العينة الصوتية — جاري معالجتها للذكاء الاصطناعي",
        "voice_sample": sample_out,
    }


@router.post("/lessons/{lesson_id}/process", response_model=ProcessResponse)
async def process_lesson_endpoint(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    result = await db.execute(
        select(Lesson).where(Lesson.id == lesson_id, Lesson.teacher_id == teacher.id)
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")
    if not lesson.pdf_path and not lesson.video_url:
        raise HTTPException(status_code=400, detail="ارفع ملف PDF أو فيديو أولاً")

    lesson = await process_lesson(db, lesson)
    return ProcessResponse(
        lesson_id=lesson.id,
        status=lesson.status.value,
        message=lesson.error_message or "اكتملت المعالجة بنجاح",
    )


@router.get("/content", response_model=list[LessonOut])
async def list_teacher_content(
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    result = await db.execute(
        select(Lesson).where(Lesson.teacher_id == teacher.id).order_by(Lesson.created_at.desc())
    )
    lessons = result.scalars().all()
    out: list[LessonOut] = []
    for lesson in lessons:
        q_count = 0
        if not is_lesson_text_too_short(lesson.preview or ""):
            q_count = await db.scalar(
                select(func.count()).select_from(QuizQuestion).where(QuizQuestion.lesson_id == lesson.id)
            )
        out.append(
            LessonOut(
                id=lesson.id,
                title=lesson.title,
                subject=lesson.subject,
                grade=lesson.grade,
                status=lesson.status.value,
                preview=lesson.preview,
                pdfUrl=_public_upload_url(lesson.pdf_path),
                page_count=lesson.page_count,
                created_at=lesson.created_at.isoformat() if lesson.created_at else None,
                students=0,
                questions=int(q_count or 0),
            )
        )
    return out


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson_endpoint(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    result = await db.execute(
        select(Lesson).where(Lesson.id == lesson_id, Lesson.teacher_id == teacher.id)
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")

    _delete_lesson_artifacts(lesson)
    await db.delete(lesson)
    await db.commit()
