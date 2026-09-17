import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_student_actor
from app.db.session import get_db
from app.models.user import User
from app.schemas.onboarding import (
    GradeUpdate,
    OnboardingCompleteOut,
    OnboardingStatusOut,
    SubjectsUpdate,
    TeachersUpdate,
)
from app.services import onboarding_service

router = APIRouter(prefix="/student/onboarding", tags=["Student Onboarding"])
logger = logging.getLogger(__name__)


@router.get("/status", response_model=OnboardingStatusOut)
async def onboarding_status(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    return await onboarding_service.get_onboarding_status(db, student.id)


@router.put("/grade", response_model=OnboardingStatusOut)
async def save_grade(
    body: GradeUpdate,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    try:
        result = await onboarding_service.save_grade(db, student.id, body.grade)
        await db.commit()
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "save_grade failed student_id=%s grade=%s: %s",
            student.id,
            body.grade,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="تعذر حفظ الصف — أعد تشغيل الخادم لتحديث قاعدة البيانات",
        ) from exc


@router.put("/subjects", response_model=OnboardingStatusOut)
async def save_subjects(
    body: SubjectsUpdate,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    status = await onboarding_service.save_subjects(db, student.id, body.subject_ids)
    await db.commit()
    return status


@router.put("/teachers", response_model=OnboardingStatusOut)
async def save_teachers(
    body: TeachersUpdate,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    status = await onboarding_service.save_teachers(db, student.id, body.choices)
    await db.commit()
    return status


@router.post("/complete", response_model=OnboardingCompleteOut)
async def complete_onboarding(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    previews, _status = await onboarding_service.complete_onboarding(db, student.id)
    await db.commit()
    return OnboardingCompleteOut(checkout_preview=previews)
