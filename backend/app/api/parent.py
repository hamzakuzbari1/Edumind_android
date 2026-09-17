from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_parent_viewer, require_student_actor
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.activity import ActivityEventOut, ParentInsightOut
from app.schemas.attendance import AttendanceSummaryOut
from app.models.student_parent_note import ParentNoteCategory
from app.schemas.parent_link import LinkedStudentOut, ParentLinkRequest, StudentLinkCodeOut
from app.services.activity_service import list_activities
from app.services.grade_report_service import list_student_grade_reports
from app.services.parent_insight_service import generate_parent_insights
from app.services.parent_link_service import (
    link_parent_to_student,
    list_linked_students,
    record_parent_view,
    resolve_parent_student_id,
    unlink_student,
)
from app.schemas.parent import CourseProgressOut, ParentAcademicIntelligenceOut, ParentDashboardOut
from app.schemas.lesson_completion import ParentLessonDetailOut, ParentLessonProgressOut
from app.services.parent_academic_intelligence_service import build_parent_academic_intelligence
from app.schemas.parent_notes import (
    ParentNoteCategoryOptionOut,
    ParentNoteListOut,
    ParentNoteOut,
    ParentNoteReplyCreateIn,
    ParentNoteReplyUpdateIn,
)
from app.schemas.parent_courses_visibility import (
    ParentCourseTeacherProfileOut,
    ParentSubjectsTeachersOut,
)
from app.schemas.parent_historical_reports import ParentHistoricalReportOut
from app.schemas.parent_notifications import ParentNotificationSettingsUpdateIn
from app.services import parent_note_service
from app.services.parent_courses_visibility_service import build_parent_subjects_teachers
from app.services.parent_historical_reports_service import build_parent_historical_report
from app.services.parent_report_export_service import (
    content_disposition_attachment,
    export_filename,
    export_report_csv,
    export_report_pdf,
    export_report_xlsx,
)
from app.services.parent_monitoring_service import (
    build_attendance,
    build_full_parent_dashboard,
    build_planner_progress,
    build_quiz_tracking,
)

router = APIRouter(prefix="/parent", tags=["Parent Monitoring"])


@router.get("/students", response_model=list[LinkedStudentOut])
async def list_students(
    parent: User = Depends(require_parent_viewer()),
    db: AsyncSession = Depends(get_db),
):
    from app.services.parent_student_context_service import build_linked_child_context

    students = await list_linked_students(db, parent.id)
    out: list[LinkedStudentOut] = []
    for student in students:
        ctx = await build_linked_child_context(db, student)
        out.append(LinkedStudentOut(**ctx))
    return out


@router.post("/link")
async def link_student(
    body: ParentLinkRequest,
    parent: User = Depends(require_parent_viewer()),
    db: AsyncSession = Depends(get_db),
):
    link = await link_parent_to_student(db, parent.id, body.link_code)
    await db.commit()
    return {"ok": True, "student_id": link.student_id}


@router.delete("/link/{student_id}")
async def unlink_linked_student(
    student_id: int,
    parent: User = Depends(require_parent_viewer()),
    db: AsyncSession = Depends(get_db),
):
    await unlink_student(db, parent.id, student_id)
    await db.commit()
    return {"ok": True}


@router.get("/dashboard", response_model=ParentDashboardOut)
async def parent_dashboard(
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    sid = await resolve_parent_student_id(db, parent, student_id)
    if parent.role == UserRole.parent:
        await record_parent_view(db, parent.id, sid)
    data = await build_full_parent_dashboard(db, parent, student_id=sid)
    await db.commit()
    return ParentDashboardOut(**data)


@router.get("/activity", response_model=list[ActivityEventOut])
async def parent_activity_feed(
    limit: int = 30,
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    sid = await resolve_parent_student_id(db, parent, student_id)
    activity = await list_activities(db, sid, limit=limit)
    return [ActivityEventOut(**a) for a in activity]


@router.get("/executive-summary")
async def parent_executive_summary(
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    from app.schemas.parent_executive_summary import ParentExecutiveSummaryOut
    from app.services.parent_executive_summary_service import build_parent_executive_summary

    sid = await resolve_parent_student_id(db, parent, student_id)
    data = await build_parent_executive_summary(db, sid, parent_id=parent.id)
    return ParentExecutiveSummaryOut(**data)


@router.get("/insights", response_model=list[ParentInsightOut])
async def parent_insights(
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    from app.models.user import User as UserModel

    sid = await resolve_parent_student_id(db, parent, student_id)
    result = await db.execute(select(UserModel).where(UserModel.id == sid))
    student = result.scalar_one_or_none()
    name = student.name.split()[0] if student and student.name else "الطالب"
    return await generate_parent_insights(db, sid, name)


@router.get("/quiz")
async def parent_quiz_tracking(
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    sid = await resolve_parent_student_id(db, parent, student_id)
    result = await db.execute(select(User).where(User.id == sid))
    student = result.scalar_one_or_none()
    name = student.name.split()[0] if student and student.name else "الطالب"
    return await build_quiz_tracking(db, sid, name)


@router.get("/attendance", response_model=AttendanceSummaryOut)
async def parent_attendance(
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    sid = await resolve_parent_student_id(db, parent, student_id)
    result = await db.execute(select(User).where(User.id == sid))
    student = result.scalar_one_or_none()
    name = student.name.split()[0] if student and student.name else "الطالب"
    data = await build_attendance(db, sid, name)
    return AttendanceSummaryOut(**data)


@router.get("/academic-intelligence", response_model=ParentAcademicIntelligenceOut)
async def parent_academic_intelligence(
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    sid = await resolve_parent_student_id(db, parent, student_id)
    data = await build_parent_academic_intelligence(db, sid)
    return ParentAcademicIntelligenceOut(**data)


@router.get("/course-progress", response_model=list[CourseProgressOut])
async def parent_course_progress(
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    sid = await resolve_parent_student_id(db, parent, student_id)
    rows = await list_student_grade_reports(db, sid)
    return [CourseProgressOut(**row) for row in rows]


@router.get("/subjects-teachers", response_model=ParentSubjectsTeachersOut)
async def parent_subjects_teachers(
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    sid = await resolve_parent_student_id(db, parent, student_id)
    return await build_parent_subjects_teachers(db, parent, sid)


@router.get("/courses/{course_id}/teacher-profile", response_model=ParentCourseTeacherProfileOut)
async def parent_course_teacher_profile(
    course_id: int,
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    from app.services.student_courses_service import get_course_teacher_profile

    sid = await resolve_parent_student_id(db, parent, student_id)
    return await get_course_teacher_profile(db, sid, course_id)


@router.get("/planner-progress")
async def parent_planner_progress(
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    from app.schemas.parent_planner_visibility import ParentPlannerVisibilityOut

    sid = await resolve_parent_student_id(db, parent, student_id)
    data = await build_planner_progress(db, sid)
    return ParentPlannerVisibilityOut(**data)


@router.get("/student-routine")
async def parent_routine_progress(
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    from app.schemas.parent_routine_visibility import ParentRoutineVisibilityOut
    from app.services.parent_monitoring_service import build_routine_progress

    sid = await resolve_parent_student_id(db, parent, student_id)
    data = await build_routine_progress(db, sid)
    return ParentRoutineVisibilityOut(**data)


@router.get("/planner-visibility")
async def parent_planner_visibility(
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    from app.schemas.parent_planner_visibility import ParentPlannerVisibilityOut
    from app.services.parent_planner_visibility_service import build_parent_planner_visibility

    sid = await resolve_parent_student_id(db, parent, student_id)
    data = await build_parent_planner_visibility(db, sid)
    return ParentPlannerVisibilityOut(**data)


@router.get("/lesson-progress", response_model=ParentLessonProgressOut)
async def parent_lesson_progress(
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    from app.services.parent_lesson_progress_service import list_parent_lesson_progress

    data = await list_parent_lesson_progress(db, parent, student_id=student_id)
    return ParentLessonProgressOut(**data)


@router.get("/lesson-progress/{lesson_id}", response_model=ParentLessonDetailOut)
async def parent_lesson_detail(
    lesson_id: int,
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    from app.services.parent_lesson_progress_service import get_parent_lesson_detail

    return ParentLessonDetailOut(**await get_parent_lesson_detail(db, parent, lesson_id, student_id=student_id))


@router.get("/link-code", response_model=StudentLinkCodeOut)
async def get_my_parent_link_code(
    student: User = Depends(require_student_actor()),
    db: AsyncSession = Depends(get_db),
):
    from app.services.parent_link_service import ensure_student_link_code

    code = await ensure_student_link_code(db, student.id)
    await db.commit()
    return StudentLinkCodeOut(link_code=code)


@router.get("/notes", response_model=ParentNoteListOut)
async def list_parent_notes(
    student_id: int | None = Query(None),
    category: ParentNoteCategory | None = Query(None),
    sort: str = Query("newest", pattern="^(newest|oldest)$"),
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    return await parent_note_service.list_parent_viewer_notes(
        db, parent, student_id=student_id, category=category, sort=sort, limit=limit
    )


@router.get("/notes/unread-count")
async def parent_notes_unread_count(
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    count = await parent_note_service.parent_unread_count(db, parent, student_id=student_id)
    return {"unread_count": count}


@router.get("/notes/categories", response_model=list[ParentNoteCategoryOptionOut])
async def parent_note_categories():
    return parent_note_service.list_category_options()


@router.get("/notes/{note_id}", response_model=ParentNoteOut)
async def get_parent_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    return await parent_note_service.get_parent_viewer_note(db, parent, note_id)


@router.post("/notes/{note_id}/read", response_model=ParentNoteOut)
async def mark_parent_note_read(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    return await parent_note_service.mark_parent_note_read(db, parent, note_id)


@router.post("/notes/{note_id}/acknowledge", response_model=ParentNoteOut)
async def acknowledge_parent_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    return await parent_note_service.acknowledge_parent_note(db, parent, note_id)


@router.post("/notes/{note_id}/reply", response_model=ParentNoteOut)
async def reply_parent_note(
    note_id: int,
    body: ParentNoteReplyCreateIn,
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    return await parent_note_service.create_note_reply(db, parent, note_id, body)


@router.patch("/notes/{note_id}/replies/{reply_id}", response_model=ParentNoteOut)
async def update_parent_note_reply(
    note_id: int,
    reply_id: int,
    body: ParentNoteReplyUpdateIn,
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    return await parent_note_service.update_note_reply(db, parent, note_id, reply_id, body)


@router.delete("/notes/{note_id}/replies/{reply_id}", response_model=ParentNoteOut)
async def delete_parent_note_reply(
    note_id: int,
    reply_id: int,
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    return await parent_note_service.delete_note_reply(db, parent, note_id, reply_id)


@router.get("/historical-report", response_model=ParentHistoricalReportOut)
async def parent_historical_report(
    student_id: int | None = Query(None),
    period: str = Query(
        "this_week",
        pattern="^(this_week|last_week|this_month|last_month|custom)$",
    ),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    import logging

    logger = logging.getLogger("eduspark.parent_reports")
    logger.info(
        "historical_report hit parent_id=%s student_id=%s period=%s",
        parent.id,
        student_id,
        period,
    )
    try:
        sid = await resolve_parent_student_id(db, parent, student_id)
        data = await build_parent_historical_report(
            db,
            sid,
            period=period,
            start_date=start_date,
            end_date=end_date,
        )
        return ParentHistoricalReportOut(**data)
    except Exception:
        logger.exception(
            "historical_report failed parent_id=%s student_id=%s period=%s",
            parent.id,
            student_id,
            period,
        )
        raise


@router.get("/historical-report/export")
async def export_parent_historical_report(
    format: str = Query("csv", pattern="^(csv|xlsx|pdf)$"),
    student_id: int | None = Query(None),
    period: str = Query(
        "this_week",
        pattern="^(this_week|last_week|this_month|last_month|custom)$",
    ),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    sid = await resolve_parent_student_id(db, parent, student_id)
    report = await build_parent_historical_report(
        db,
        sid,
        period=period,
        start_date=start_date,
        end_date=end_date,
    )

    if format == "csv":
        content = export_report_csv(report)
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers=content_disposition_attachment(export_filename(report, "csv")),
        )
    if format == "xlsx":
        try:
            content = export_report_xlsx(report)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=content_disposition_attachment(export_filename(report, "xlsx")),
        )
    import logging

    logging.getLogger("eduspark.pdf_export").warning(
        "PDF_API_HANDLER export_parent_historical_report format=pdf student_id=%s",
        sid,
    )
    content = export_report_pdf(report)
    return Response(
        content=content,
        media_type="application/pdf",
        headers=content_disposition_attachment(export_filename(report, "pdf")),
    )


@router.get("/notifications")
async def parent_notifications(
    student_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    from app.schemas.parent_notifications import ParentNotificationListOut
    from app.services import parent_notification_service

    sid = await resolve_parent_student_id(db, parent, student_id)
    data = await parent_notification_service.list_parent_notifications(
        db, parent.id, sid, limit=limit
    )
    await db.commit()
    return ParentNotificationListOut(**data)


@router.post("/notifications/{notification_id}/read")
async def mark_parent_notification_read(
    notification_id: int,
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    from app.schemas.parent_notifications import ParentNotificationOut
    from app.services import parent_notification_service

    sid = await resolve_parent_student_id(db, parent, student_id)
    row = await parent_notification_service.mark_parent_notification_read(
        db, parent.id, sid, notification_id
    )
    await db.commit()
    return ParentNotificationOut(**row)


@router.get("/notification-settings")
async def get_parent_notification_settings(
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    from app.schemas.parent_notifications import ParentNotificationSettingsOut
    from app.services import parent_notification_service

    sid = await resolve_parent_student_id(db, parent, student_id)
    row = await parent_notification_service.get_notification_settings(db, parent.id, sid)
    await db.commit()
    return ParentNotificationSettingsOut(**parent_notification_service.settings_to_dict(row))


@router.put("/notification-settings")
async def update_parent_notification_settings(
    body: ParentNotificationSettingsUpdateIn,
    student_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    parent: User = Depends(require_parent_viewer()),
):
    from app.schemas.parent_notifications import ParentNotificationSettingsOut
    from app.services import parent_notification_service

    sid = await resolve_parent_student_id(db, parent, student_id)
    row = await parent_notification_service.update_notification_settings(
        db,
        parent.id,
        sid,
        login_alerts=body.login_alerts,
        logout_alerts=body.logout_alerts,
        lesson_alerts=body.lesson_alerts,
        quiz_alerts=body.quiz_alerts,
        low_score_alerts=body.low_score_alerts,
        inactivity_alerts=body.inactivity_alerts,
        planner_alerts=body.planner_alerts,
        inactivity_days=body.inactivity_days,
        low_score_threshold=body.low_score_threshold,
    )
    await db.commit()
    return ParentNotificationSettingsOut(**parent_notification_service.settings_to_dict(row))
