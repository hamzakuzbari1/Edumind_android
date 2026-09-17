"""Unified lesson publish — course + video/PDF + AI pipeline (voice from teacher profile)."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.lesson_publish import LessonPublishOut, LessonPublishStatusOut
from app.services import lesson_publish_service

router = APIRouter(prefix="/teacher", tags=["Lesson Publish"])
settings = get_settings()


@router.post("/lessons/publish", response_model=LessonPublishOut)
async def publish_lesson(
    grade: int = Form(...),
    subject_id: int = Form(...),
    title: str = Form(...),
    description: str | None = Form(None),
    sort_order: int = Form(0),
    course_id: int | None = Form(None),
    video: UploadFile | None = File(None),
    pdf: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    video_bytes = video_name = pdf_bytes = pdf_name = None
    if video and video.filename:
        video_bytes = await video.read()
        video_name = video.filename
    if pdf and pdf.filename:
        pdf_bytes = await pdf.read()
        pdf_name = pdf.filename

    if video_bytes and len(video_bytes) > settings.MAX_PDF_BYTES * 4:
        raise HTTPException(status_code=400, detail="حجم الفيديو كبير جداً")
    if pdf_bytes and len(pdf_bytes) > settings.MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="حجم ملف PDF كبير جداً")

    return await lesson_publish_service.publish_lesson(
        db,
        teacher,
        grade=grade,
        subject_id=subject_id,
        title=title,
        description=description,
        sort_order=sort_order,
        course_id=course_id,
        video_bytes=video_bytes,
        video_filename=video_name,
        pdf_bytes=pdf_bytes,
        pdf_filename=pdf_name,
    )


@router.get("/lessons/{lesson_id}/publish-status", response_model=LessonPublishStatusOut)
async def lesson_publish_status(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await lesson_publish_service.get_publish_status(db, teacher, lesson_id)
