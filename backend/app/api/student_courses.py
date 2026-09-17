import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import require_student_actor
from app.db.session import get_db
from app.models.user import User
from app.schemas.messaging import CourseMessageTeacherIn, CourseMessageTeacherOut
from app.schemas.lesson_completion import (
    CourseLessonProgressSummaryOut,
    LessonProgressOut,
    LessonProgressUpdateIn,
    ParentLessonDetailOut,
    ParentLessonProgressOut,
    VerifyCompletionOut,
)
from app.schemas.student_courses import (
    CourseLessonOut,
    StudentCourseDetailOut,
    StudentCourseResumeLessonOut,
    StudentCourseTeacherProfileOut,
    StudentCourseUnitOut,
    StudentDashboardOut,
    StudentLessonStatusOut,
)
from app.schemas.subscriptions import SubscribeCourseOut, SubscribeCourseRequest, SubscriptionsCatalogOut
from app.services import lesson_completion_service, messaging_service, student_courses_service, subscription_service

router = APIRouter(prefix="/student", tags=["Student Courses"])
logger = logging.getLogger(__name__)
settings = get_settings()


@router.get("/dashboard", response_model=StudentDashboardOut)
async def student_dashboard(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    try:
        result = await student_courses_service.list_student_dashboard(db, student.id)
        await db.commit()
        logger.info(
            "GET /student/dashboard ok student_id=%s grade=%s courses=%s",
            student.id,
            result.grade,
            len(result.courses),
        )
        return result
    except Exception as exc:
        logger.exception(
            "GET /student/dashboard failed student_id=%s email=%s: %s: %s",
            student.id,
            student.email,
            type(exc).__name__,
            exc,
        )
        if settings.DEBUG:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"{type(exc).__name__}: {exc}",
            ) from exc
        raise


@router.get("/courses/{course_id}", response_model=StudentCourseDetailOut)
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    return await student_courses_service.get_student_course(db, student.id, course_id)


@router.get("/courses/{course_id}/units", response_model=list[StudentCourseUnitOut])
async def get_course_units(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    return await student_courses_service.list_student_course_units(db, student.id, course_id)


@router.get("/courses/{course_id}/resume", response_model=StudentCourseResumeLessonOut | None)
async def get_course_resume(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    course = await student_courses_service.get_student_course(db, student.id, course_id)
    return course.resume_lesson


@router.get("/courses/{course_id}/teacher-profile", response_model=StudentCourseTeacherProfileOut)
async def get_course_teacher_profile(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    return await student_courses_service.get_course_teacher_profile(db, student.id, course_id)


@router.get("/lessons/{lesson_id}", response_model=CourseLessonOut)
async def get_lesson(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    return await student_courses_service.get_student_lesson(db, student.id, lesson_id)


@router.post(
    "/courses/{course_id}/open-teacher-chat",
    response_model=CourseMessageTeacherOut,
)
async def open_course_teacher_chat(
    course_id: int,
    body: CourseMessageTeacherIn,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    result = await messaging_service.open_course_teacher_conversation(
        db, student, course_id, include_parent=body.include_parent
    )
    await db.commit()
    return result


@router.get("/subscriptions", response_model=SubscriptionsCatalogOut)
async def subscriptions_catalog(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    result = await student_courses_service.list_subscriptions_catalog(db, student.id)
    await db.commit()
    return result


@router.post("/subscriptions/subscribe", response_model=SubscribeCourseOut)
async def subscribe_to_course(
    body: SubscribeCourseRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    result = await subscription_service.subscribe_course(
        db, student.id, body.course_id, body.method
    )
    await db.commit()
    return result


@router.get("/lessons/{lesson_id}/progress", response_model=LessonProgressOut)
async def get_lesson_progress(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    data = await lesson_completion_service.progress_to_dict(db, student.id, lesson_id)
    await db.commit()
    return LessonProgressOut(**data)


@router.post("/lessons/{lesson_id}/progress", response_model=LessonProgressOut)
async def update_lesson_progress(
    lesson_id: int,
    body: LessonProgressUpdateIn,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    data = await lesson_completion_service.update_lesson_progress(
        db,
        student.id,
        lesson_id,
        video_percent=body.video_percent,
        pdf_percent=body.pdf_percent,
        pdf_opened=body.pdf_opened,
    )
    await db.commit()
    return LessonProgressOut(**data)


@router.post("/lessons/{lesson_id}/verify-completion", response_model=VerifyCompletionOut)
async def verify_lesson_completion(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    result = await lesson_completion_service.verify_lesson_completion(db, student.id, lesson_id)
    await db.commit()
    progress = result.get("progress")
    return VerifyCompletionOut(
        success=result["success"],
        message=result["message"],
        checklist=result.get("checklist") or [],
        progress=LessonProgressOut(**progress) if progress else None,
    )


@router.get("/courses/{course_id}/lesson-progress", response_model=CourseLessonProgressSummaryOut)
async def course_lesson_progress_summary(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    course = await student_courses_service.get_student_course(db, student.id, course_id)
    completed = [l.id for l in course.lessons if l.completed]
    pending = [l.id for l in course.lessons if not l.completed and (l.completion_percent or 0) == 0]
    in_progress = [
        l.id for l in course.lessons if not l.completed and (l.completion_percent or 0) > 0
    ]
    total = len(course.lessons)
    return CourseLessonProgressSummaryOut(
        completed_count=len(completed),
        pending_count=len(pending),
        in_progress_count=len(in_progress),
        completion_percent=round((len(completed) / total) * 100) if total else 0,
        completed_lesson_ids=completed,
        pending_lesson_ids=pending,
        in_progress_lesson_ids=in_progress,
    )


@router.post("/lessons/{lesson_id}/complete", status_code=410)
async def complete_lesson(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    """Deprecated — completion is automatic when learning requirements are met."""
    await student_courses_service.mark_lesson_complete(db, student.id, lesson_id)


@router.get("/lessons/{lesson_id}/status", response_model=StudentLessonStatusOut)
async def lesson_ai_status(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    return await student_courses_service.get_lesson_status(db, student.id, lesson_id)
