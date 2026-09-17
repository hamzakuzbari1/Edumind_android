"""Student activity tracking — sessions, engagement events, study time."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthContext, get_auth_context, require_parent_viewer, require_student_actor
from app.db.session import get_db
from app.models.student_activity_tracking import EngagementEventType
from app.models.user import User
from app.schemas.activity_tracking import (
    ActivitySessionOut,
    EngagementEventIn,
    EngagementEventOut,
    StudentActivitySummaryOut,
)
from app.schemas.parent_attendance_analytics import ParentAttendanceAnalyticsOut
from app.services import parent_attendance_analytics_service, student_activity_tracking_service
from app.services.parent_link_service import resolve_parent_student_id

router = APIRouter(prefix="/student/activity", tags=["Student Activity Tracking"])

_VALID_EVENTS = {member.value for member in EngagementEventType}


@router.get("/summary", response_model=StudentActivitySummaryOut)
async def activity_summary(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    data = await student_activity_tracking_service.get_student_activity_summary(db, student.id)
    return StudentActivitySummaryOut(**data)


@router.get("/sessions", response_model=list[ActivitySessionOut])
async def activity_sessions(
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    rows = await student_activity_tracking_service.list_activity_sessions(db, student.id, limit=limit)
    return [ActivitySessionOut(**row) for row in rows]


@router.get("/events", response_model=list[EngagementEventOut])
async def activity_events(
    limit: int = Query(50, ge=1, le=200),
    event_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    et = None
    if event_type:
        if event_type not in _VALID_EVENTS:
            raise HTTPException(status_code=400, detail="نوع النشاط غير مدعوم")
        et = EngagementEventType(event_type)
    rows = await student_activity_tracking_service.list_engagement_events(
        db, student.id, limit=limit, event_type=et
    )
    return [EngagementEventOut(**row) for row in rows]


@router.post("/events", response_model=EngagementEventOut)
async def record_activity_event(
    body: EngagementEventIn,
    ctx: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    if body.event_type not in _VALID_EVENTS:
        raise HTTPException(status_code=400, detail="نوع النشاط غير مدعوم")
    if body.event_type in {"login", "logout", "session_expired", "session_inactive"}:
        raise HTTPException(status_code=400, detail="لا يمكن تسجيل أحداث الجلسة يدوياً")

    event = await student_activity_tracking_service.record_engagement_event(
        db,
        student.id,
        EngagementEventType(body.event_type),
        auth_session_id=ctx.session_id,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        path=body.path,
        metadata=body.metadata,
    )
    await db.commit()
    return EngagementEventOut(
        id=event.id,
        event_type=event.event_type.value,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        path=event.path,
        counted_seconds=int(event.counted_seconds or 0),
        occurred_at=event.occurred_at.isoformat() if event.occurred_at else None,
    )


parent_router = APIRouter(prefix="/parent/activity-tracking", tags=["Parent Activity Tracking"])


@parent_router.get("/summary", response_model=StudentActivitySummaryOut)
async def parent_activity_summary(
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    sid = await resolve_parent_student_id(db, parent, student_id)
    data = await student_activity_tracking_service.get_student_activity_summary(db, sid)
    return StudentActivitySummaryOut(**data)


@parent_router.get("/sessions", response_model=list[ActivitySessionOut])
async def parent_activity_sessions(
    student_id: int | None = Query(None),
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    sid = await resolve_parent_student_id(db, parent, student_id)
    rows = await student_activity_tracking_service.list_activity_sessions(db, sid, limit=limit)
    return [ActivitySessionOut(**row) for row in rows]


@parent_router.get("/events", response_model=list[EngagementEventOut])
async def parent_activity_events(
    student_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    event_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    sid = await resolve_parent_student_id(db, parent, student_id)
    et = None
    if event_type:
        if event_type not in _VALID_EVENTS:
            raise HTTPException(status_code=400, detail="نوع النشاط غير مدعوم")
        et = EngagementEventType(event_type)
    rows = await student_activity_tracking_service.list_engagement_events(
        db, sid, limit=limit, event_type=et
    )
    return [EngagementEventOut(**row) for row in rows]


@parent_router.get("/analytics", response_model=ParentAttendanceAnalyticsOut)
async def parent_attendance_analytics(
    student_id: int | None = Query(None),
    week_offset: int = Query(0, ge=0, le=52),
    month_offset: int = Query(0, ge=0, le=24),
    session_limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    sid = await resolve_parent_student_id(db, parent, student_id)
    data = await parent_attendance_analytics_service.build_parent_attendance_analytics(
        db,
        sid,
        week_offset=week_offset,
        month_offset=month_offset,
        session_limit=session_limit,
    )
    return ParentAttendanceAnalyticsOut(**data)
