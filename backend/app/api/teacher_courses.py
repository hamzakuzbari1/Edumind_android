from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.teacher_courses import (
    TeacherCourseCreate,
    TeacherCourseFormContextOut,
    TeacherCourseLessonOut,
    TeacherCourseOut,
    TeacherCourseUpdate,
    TeacherLessonPreviewOut,
    TeacherLessonUpdate,
)
from app.services import teacher_courses_service
from app.services.lesson_processing_tasks import schedule_lesson_processing

router = APIRouter(prefix="/teacher", tags=["Teacher Courses"])
settings = get_settings()


def _ensure_valid_pdf(data: bytes) -> None:
    if not data.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="الملف المرفوع ليس ملف PDF صالح")


@router.get("/courses/form-context", response_model=TeacherCourseFormContextOut)
async def course_form_context(
    grade: int | None = None,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    result = await teacher_courses_service.get_form_context(db, teacher, grade)
    await db.commit()
    return result


@router.get("/courses", response_model=list[TeacherCourseOut])
async def list_courses(
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    result = await teacher_courses_service.list_teacher_courses(db, teacher)
    await db.commit()
    return result


@router.post("/courses", response_model=TeacherCourseOut)
async def create_course_json(
    body: TeacherCourseCreate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    result = await teacher_courses_service.create_course(db, teacher, body)
    await db.commit()
    return result


@router.post("/courses/create", response_model=TeacherCourseOut)
async def create_course_multipart(
    title: str = Form(...),
    subject_id: int = Form(...),
    grade: int = Form(...),
    price: float = Form(0),
    description: str | None = Form(None),
    is_published: bool = Form(True),
    thumbnail: UploadFile | None = File(None),
    banner: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    thumb_bytes = thumb_name = banner_bytes = banner_name = None
    if thumbnail and thumbnail.filename:
        thumb_bytes = await thumbnail.read()
        thumb_name = thumbnail.filename
    if banner and banner.filename:
        banner_bytes = await banner.read()
        banner_name = banner.filename

    result = await teacher_courses_service.create_course_with_media(
        db,
        teacher,
        title=title,
        description=description,
        subject_id=subject_id,
        grade=grade,
        price=price,
        is_published=is_published,
        thumbnail_bytes=thumb_bytes,
        thumbnail_name=thumb_name,
        banner_bytes=banner_bytes,
        banner_name=banner_name,
    )
    await db.commit()
    return result


@router.put("/courses/{course_id}", response_model=TeacherCourseOut)
async def update_course(
    course_id: int,
    body: TeacherCourseUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    result = await teacher_courses_service.update_course(db, teacher, course_id, body)
    await db.commit()
    return result


@router.get("/courses/{course_id}/lessons", response_model=list[TeacherCourseLessonOut])
async def list_course_lessons(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_courses_service.list_course_lessons(db, teacher, course_id)


@router.get(
    "/courses/{course_id}/lessons/{lesson_id}",
    response_model=TeacherLessonPreviewOut,
)
async def get_course_lesson(
    course_id: int,
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_courses_service.get_course_lesson_detail(db, teacher, course_id, lesson_id)


@router.patch(
    "/courses/{course_id}/lessons/{lesson_id}",
    response_model=TeacherLessonPreviewOut,
)
async def update_course_lesson(
    course_id: int,
    lesson_id: int,
    body: TeacherLessonUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    result = await teacher_courses_service.update_course_lesson(
        db, teacher, course_id, lesson_id, body
    )
    await db.commit()
    return result


def _form_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "yes", "on")


@router.post(
    "/courses/{course_id}/lessons/{lesson_id}/update-content",
    response_model=TeacherLessonPreviewOut,
)
async def update_course_lesson_content(
    course_id: int,
    lesson_id: int,
    title: str = Form(...),
    description: str | None = Form(None),
    is_visible: str = Form("true"),
    remove_video: str = Form("false"),
    remove_pdf: str = Form("false"),
    remove_audio: str = Form("false"),
    video: UploadFile | None = File(None),
    pdf: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    video_bytes = video_name = pdf_bytes = pdf_name = audio_bytes = audio_name = None
    if video and video.filename:
        video_bytes = await video.read()
        video_name = video.filename
        if len(video_bytes) > settings.MAX_PDF_BYTES * 4:
            raise HTTPException(status_code=400, detail="حجم الفيديو كبير جداً")
    if pdf and pdf.filename:
        pdf_bytes = await pdf.read()
        pdf_name = pdf.filename
        if len(pdf_bytes) > settings.MAX_PDF_BYTES:
            raise HTTPException(status_code=400, detail="حجم ملف PDF كبير جداً")
        _ensure_valid_pdf(pdf_bytes)
    if audio and audio.filename:
        audio_bytes = await audio.read()
        audio_name = audio.filename
        if len(audio_bytes) > settings.MAX_PDF_BYTES:
            raise HTTPException(status_code=400, detail="حجم الملف الصوتي كبير جداً")

    result, schedule_ai = await teacher_courses_service.update_course_lesson_content(
        db,
        teacher,
        course_id,
        lesson_id,
        title=title,
        description=description,
        is_visible=_form_bool(is_visible),
        remove_video=_form_bool(remove_video),
        remove_pdf=_form_bool(remove_pdf),
        remove_audio=_form_bool(remove_audio),
        video_bytes=video_bytes,
        video_filename=video_name,
        pdf_bytes=pdf_bytes,
        pdf_filename=pdf_name,
        audio_bytes=audio_bytes,
        audio_filename=audio_name,
    )
    await db.commit()
    if schedule_ai:
        schedule_lesson_processing(lesson_id)
    return result


@router.post("/courses/{course_id}/lessons/full", response_model=TeacherCourseLessonOut)
async def upload_full_lesson(
    course_id: int,
    title: str = Form(...),
    description: str | None = Form(None),
    sort_order: int = Form(0),
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
    if pdf_bytes:
        _ensure_valid_pdf(pdf_bytes)

    result, schedule = await teacher_courses_service.create_lesson_with_assets(
        db,
        teacher,
        course_id,
        title=title,
        description=description,
        sort_order=sort_order,
        video_bytes=video_bytes,
        video_filename=video_name,
        pdf_bytes=pdf_bytes,
        pdf_filename=pdf_name,
    )
    await db.commit()
    if schedule:
        schedule_lesson_processing(result.id)
    return result


@router.post("/courses/{course_id}/lessons", response_model=TeacherCourseLessonOut)
async def create_course_lesson(
    course_id: int,
    title: str = Form(...),
    description: str | None = Form(None),
    sort_order: int = Form(0),
    video: UploadFile | None = File(None),
    pdf: UploadFile | None = File(None),
    video_url: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    """Create one lesson with optional video + PDF in the same request."""
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
    if pdf_bytes:
        _ensure_valid_pdf(pdf_bytes)

    external_video_url = (video_url or "").strip() or None
    if video_bytes and external_video_url:
        raise HTTPException(status_code=400, detail="اختر مصدراً واحداً فقط: ملف فيديو أو رابط")

    result, schedule = await teacher_courses_service.create_lesson_with_assets(
        db,
        teacher,
        course_id,
        title=title,
        description=description,
        sort_order=sort_order,
        video_bytes=video_bytes,
        video_filename=video_name,
        pdf_bytes=pdf_bytes,
        pdf_filename=pdf_name,
        external_video_url=external_video_url,
    )
    await db.commit()
    if schedule:
        schedule_lesson_processing(result.id)
    return result


@router.post("/courses/{course_id}/lessons/video", response_model=TeacherCourseLessonOut)
async def upload_video_lesson(
    course_id: int,
    title: str = Form(...),
    description: str | None = Form(None),
    sort_order: int = Form(0),
    lesson_id: int | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    data = await file.read()
    if len(data) > settings.MAX_PDF_BYTES * 4:
        raise HTTPException(status_code=400, detail="حجم الفيديو كبير جداً")

    result, schedule = await teacher_courses_service.add_video_lesson(
        db,
        teacher,
        course_id,
        title=title,
        description=description,
        sort_order=sort_order,
        video_bytes=data,
        filename=file.filename or "video.mp4",
        lesson_id=lesson_id,
    )
    await db.commit()
    if schedule:
        schedule_lesson_processing(result.id)
    return result


@router.post("/courses/{course_id}/lessons/pdf", response_model=TeacherCourseLessonOut)
async def upload_pdf_lesson(
    course_id: int,
    title: str = Form(...),
    description: str | None = Form(None),
    sort_order: int = Form(0),
    lesson_id: int | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    data = await file.read()
    if len(data) > settings.MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="حجم الملف كبير جداً")
    _ensure_valid_pdf(data)

    result, schedule = await teacher_courses_service.add_pdf_lesson(
        db,
        teacher,
        course_id,
        title=title,
        description=description,
        sort_order=sort_order,
        pdf_bytes=data,
        filename=file.filename or "file.pdf",
        lesson_id=lesson_id,
    )
    await db.commit()
    if schedule:
        schedule_lesson_processing(result.id)
    return result


@router.post("/courses/{course_id}/lessons/homework", response_model=TeacherCourseLessonOut)
async def upload_homework_lesson(
    course_id: int,
    title: str = Form(...),
    description: str | None = Form(None),
    sort_order: int = Form(0),
    lesson_id: int | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    data = await file.read()
    if len(data) > settings.MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="حجم الملف كبير جداً")
    _ensure_valid_pdf(data)

    result = await teacher_courses_service.add_homework_lesson(
        db,
        teacher,
        course_id,
        title=title,
        description=description,
        sort_order=sort_order,
        file_bytes=data,
        filename=file.filename or "homework.pdf",
        lesson_id=lesson_id,
    )
    await db.commit()
    return result


@router.post("/courses/{course_id}/lessons/smart-pdf", response_model=TeacherCourseLessonOut)
async def upload_smart_pdf_lesson(
    course_id: int,
    title: str = Form(...),
    description: str | None = Form(None),
    sort_order: int = Form(0),
    lesson_id: int | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    data = await file.read()
    if len(data) > settings.MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="حجم الملف كبير جداً")
    _ensure_valid_pdf(data)

    result, schedule = await teacher_courses_service.add_smart_pdf_lesson(
        db,
        teacher,
        course_id,
        title=title,
        description=description,
        sort_order=sort_order,
        pdf_bytes=data,
        filename=file.filename or "lesson.pdf",
        lesson_id=lesson_id,
    )
    await db.commit()
    if schedule:
        schedule_lesson_processing(result.id)
    return result


@router.post("/courses/{course_id}/lessons/{lesson_id}/process")
async def process_course_lesson(
    course_id: int,
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    result = await teacher_courses_service.process_course_lesson(db, teacher, course_id, lesson_id)
    await db.commit()
    return result


@router.post("/courses/{course_id}/lessons/{lesson_id}/quiz/regenerate")
async def regenerate_course_lesson_quiz(
    course_id: int,
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    result = await teacher_courses_service.regenerate_course_lesson_quiz(
        db, teacher, course_id, lesson_id
    )
    await db.commit()
    return result
