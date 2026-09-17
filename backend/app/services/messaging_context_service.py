"""Student/parent context panels for teacher messaging workspace."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import ConversationParticipantRole, ConversationThread, ConversationThreadType
from app.models.student_parent_note import StudentParentNote
from app.models.user import User, UserRole
from app.schemas.messaging import (
    MessagingParentContextOut,
    MessagingSnapshotItemOut,
    MessagingSnapshotOut,
    MessagingStudentContextOut,
    MessagingThreadContextOut,
)
from app.services import messaging_service
from app.services.parent_note_service import list_teacher_parent_notes
from app.services.teacher_student_service import (
    assert_student_in_teacher_scope,
    get_teacher_student_profile,
    search_teacher_students,
)


async def get_thread_context(
    db: AsyncSession, teacher: User, thread_id: int
) -> MessagingThreadContextOut:
    if teacher.role != UserRole.teacher:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="للمعلمين فقط")

    await messaging_service._assert_participant(db, thread_id, teacher)
    thread = await db.get(ConversationThread, thread_id)
    if not thread:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة غير موجودة")

    thread_type = (
        thread.thread_type
        if isinstance(thread.thread_type, ConversationThreadType)
        else ConversationThreadType(thread.thread_type)
    )

    student_ctx = None
    parent_ctx = None
    snapshot = None

    if thread_type in (
        ConversationThreadType.teacher_student,
        ConversationThreadType.teacher_student_parent,
    ):
        await assert_student_in_teacher_scope(db, teacher, thread.student_id)
        student_ctx = await _build_student_context(db, teacher, thread.student_id)
        snapshot = await _build_student_snapshot(db, teacher, thread.student_id)

    if thread_type in (
        ConversationThreadType.teacher_parent,
        ConversationThreadType.teacher_student_parent,
    ):
        parent_ctx = await _build_parent_context(db, thread)

    course_label = None
    if thread.course_id:
        _, course_label, _ = await messaging_service._course_context_fields(db, thread)

    return MessagingThreadContextOut(
        thread_id=thread.id,
        thread_type=thread_type,
        course_context_label=course_label,
        student=student_ctx,
        parent=parent_ctx,
        snapshot=snapshot,
    )


async def _build_student_context(
    db: AsyncSession, teacher: User, student_id: int
) -> MessagingStudentContextOut:
    search = await search_teacher_students(db, teacher)
    row = next((s for s in search.students if s.student_id == student_id), None)
    profile = await get_teacher_student_profile(db, teacher, student_id)

    status_label = "نشط" if (row and row.is_active) else "غير نشط"
    if profile.info.account_status == "expired":
        status_label = "غير نشط"

    return MessagingStudentContextOut(
        student_id=student_id,
        full_name=profile.info.full_name,
        grade=profile.info.grade,
        status=status_label,
        is_active=row.is_active if row else profile.info.account_status == "active",
        last_activity_at=row.last_activity_at if row else profile.analytics.last_active_date,
        completion_percent=profile.analytics.completion_percent,
        average_quiz_percent=profile.analytics.average_score_percent,
        current_streak=profile.analytics.active_streak,
        enrolled_subjects=profile.learning.enrolled_subjects,
        avatar_url=None,
    )


async def _build_parent_context(db: AsyncSession, thread: ConversationThread) -> MessagingParentContextOut | None:
    from app.models.conversation import ConversationParticipant

    result = await db.execute(
        select(ConversationParticipant, User)
        .join(User, User.id == ConversationParticipant.user_id)
        .where(
            ConversationParticipant.thread_id == thread.id,
            ConversationParticipant.role == ConversationParticipantRole.parent,
        )
        .limit(1)
    )
    row = result.first()
    if not row:
        return None
    _part, parent_user = row
    student = await db.get(User, thread.student_id)
    from app.models.profile import StudentProfile

    grade = await db.scalar(select(StudentProfile.grade).where(StudentProfile.user_id == thread.student_id))
    return MessagingParentContextOut(
        parent_id=parent_user.id,
        parent_name=parent_user.name,
        linked_student_id=thread.student_id,
        linked_student_name=student.name if student else "—",
        student_grade=grade,
    )


async def _build_student_snapshot(
    db: AsyncSession, teacher: User, student_id: int
) -> MessagingSnapshotOut:
    profile = await get_teacher_student_profile(db, teacher, student_id)

    latest_quiz = None
    if profile.quiz_analytics.recent_attempts:
        q = profile.quiz_analytics.recent_attempts[0]
        latest_quiz = MessagingSnapshotItemOut(
            title=q.quiz_title,
            subtitle=f"{q.score_percent}% — {q.course_title}",
            occurred_at=q.submitted_at,
        )

    latest_lesson = None
    for act in profile.activity_timeline:
        if act.event_type in ("lesson_complete", "lesson_progress", "lesson"):
            latest_lesson = MessagingSnapshotItemOut(
                title=act.title,
                subtitle=act.description,
                occurred_at=act.occurred_at,
            )
            break

    latest_note = None
    if profile.notes:
        n = profile.notes[0]
        latest_note = MessagingSnapshotItemOut(
            title="ملاحظة خاصة",
            subtitle=n.note_text[:120],
            occurred_at=n.created_at,
        )

    latest_parent = None
    notes_page = await list_teacher_parent_notes(db, teacher, student_id, limit=1)
    if notes_page.notes:
        pn = notes_page.notes[0]
        latest_parent = MessagingSnapshotItemOut(
            title=pn.title or "ملاحظة لولي الأمر",
            subtitle=(pn.description or "")[:120],
            occurred_at=pn.created_at,
        )

    return MessagingSnapshotOut(
        latest_quiz=latest_quiz,
        latest_lesson_activity=latest_lesson,
        latest_teacher_note=latest_note,
        latest_parent_interaction=latest_parent,
    )
