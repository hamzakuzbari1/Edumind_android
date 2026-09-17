"""Self-contained Grammar & Vocabulary teaching lessons — its own router."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.language_lessons import LessonListOut, LessonOut
from app.services.language_access_service import require_language_learning_ready
from app.services.language_lessons_service import get_lesson, list_lessons

router = APIRouter(prefix="/student/languages/lessons", tags=["Language Lessons"])


@router.get("", response_model=LessonListOut)
async def lessons_list(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    payload = await list_lessons(db, student_id=student.id)
    return LessonListOut(**payload)


@router.get("/{lesson_id}", response_model=LessonOut)
async def lesson_detail(
    lesson_id: str,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    lesson = await get_lesson(db, student_id=student.id, lesson_id=lesson_id)
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return LessonOut(**lesson)
