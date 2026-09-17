from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.academic_grades import MIN_ACADEMIC_GRADE, MAX_ACADEMIC_GRADE
from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.catalog import GradeOut, SubjectOut, TeacherCardOut
from app.services import catalog_service

router = APIRouter(prefix="/catalog", tags=["Catalog"])


@router.get("/grades", response_model=list[GradeOut])
async def list_grades(_user=Depends(get_current_user)):
    return catalog_service.list_grades()


@router.get("/subjects", response_model=list[SubjectOut])
async def list_subjects(
    grade: int = Query(..., ge=MIN_ACADEMIC_GRADE, le=MAX_ACADEMIC_GRADE),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await catalog_service.list_subjects_for_grade(db, grade)


@router.get("/teachers", response_model=list[TeacherCardOut])
async def list_teachers(
    subject_id: int = Query(...),
    grade: int = Query(..., ge=MIN_ACADEMIC_GRADE, le=MAX_ACADEMIC_GRADE),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await catalog_service.list_teachers_for_subject(db, subject_id=subject_id, grade=grade)
