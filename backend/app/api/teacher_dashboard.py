from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.teacher_dashboard import TeacherCourseDetailOut, TeacherGradesOut, TeacherOverviewOut
from app.services import teacher_dashboard_service

router = APIRouter(prefix="/teacher/dashboard", tags=["Teacher Dashboard"])


@router.get("/overview", response_model=TeacherOverviewOut)
async def overview(
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_dashboard_service.teacher_overview(db, teacher)


@router.get("/grades", response_model=TeacherGradesOut)
async def grades(
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_dashboard_service.teacher_grades(db, teacher)


@router.get("/courses/{course_id}", response_model=TeacherCourseDetailOut)
async def course_detail(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_dashboard_service.teacher_course_detail(db, teacher, course_id)
