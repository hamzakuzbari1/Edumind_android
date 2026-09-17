from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_auth_context, AuthContext
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.attendance import AttendanceRecordOut, AttendanceSummaryOut
from app.services.attendance_service import (
    build_attendance_summary,
    list_records,
    record_to_out,
)
from app.services.parent_monitoring_service import _resolve_student_id

router = APIRouter(prefix="/attendance", tags=["Attendance"])


async def _student_for_request(ctx: AuthContext, db: AsyncSession) -> tuple[User, int]:
    if ctx.is_parent_viewer:
        if ctx.user.role != UserRole.student:
            raise HTTPException(status_code=403, detail="وضع ولي الأمر متاح لحسابات الطلاب فقط")
        student = ctx.user
        return student, student.id
    if ctx.user.role == UserRole.student:
        return ctx.user, ctx.user.id
    student_id = await _resolve_student_id(db, ctx.user)
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="الطالب غير موجود")
    return student, student_id


def _auth_dep():
    """Parent viewer or student may read attendance."""

    async def checker(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if ctx.is_parent_viewer or ctx.user.role == UserRole.student:
            return ctx
        raise HTTPException(status_code=403, detail="غير مصرح بعرض الحضور")

    return checker


@router.get("/summary", response_model=AttendanceSummaryOut)
async def attendance_summary(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(_auth_dep()),
):
    student, student_id = await _student_for_request(ctx, db)
    name = student.name.split()[0] if student.name else "الطالب"
    data = await build_attendance_summary(db, student_id, name)
    return AttendanceSummaryOut(**data)


@router.get("/records", response_model=list[AttendanceRecordOut])
async def attendance_records(
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(_auth_dep()),
):
    _, student_id = await _student_for_request(ctx, db)
    records = await list_records(db, student_id, from_date=from_date, to_date=to_date)
    return [AttendanceRecordOut(**record_to_out(r)) for r in records]


@router.get("/weekly", response_model=AttendanceSummaryOut)
async def attendance_weekly(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(_auth_dep()),
):
    """Weekly slice (calendar + metrics) — same summary engine, week-focused."""
    return await attendance_summary(db=db, ctx=ctx)


@router.get("/monthly", response_model=AttendanceSummaryOut)
async def attendance_monthly(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(_auth_dep()),
):
    """Monthly overview included in summary payload."""
    return await attendance_summary(db=db, ctx=ctx)
