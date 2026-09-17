"""Parent notes: threads, replies, acknowledgement, notifications."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import TeacherProfile
from app.models.parent_link import ParentStudentLink
from app.models.student_parent_note import (
    ParentNoteAuthorRole,
    ParentNoteCategory,
    ParentNotePriority,
    ParentNoteStatus,
    StudentParentNote,
    StudentParentNoteRead,
    StudentParentNoteReply,
)
from app.models.user import User, UserRole
from app.schemas.parent_notes import (
    ParentNoteCategoryOptionOut,
    ParentNoteCreateIn,
    ParentNoteListOut,
    ParentNoteOut,
    ParentNotePriorityOptionOut,
    ParentNoteReadByOut,
    ParentNoteReplyCreateIn,
    ParentNoteReplyOut,
    ParentNoteReplyUpdateIn,
    ParentNoteStatusOptionOut,
    ParentNoteUpdateIn,
)
from app.models.notification import NotificationType
from app.services import notification_service
from app.services.parent_link_service import resolve_parent_student_id
from app.services.teacher_student_service import assert_student_in_teacher_scope
from app.services.teacher_setup_service import get_or_create_teacher_profile

CATEGORY_LABELS_AR = {
    ParentNoteCategory.academic: "أكاديمي",
    ParentNoteCategory.attendance: "حضور",
    ParentNoteCategory.homework: "واجبات",
    ParentNoteCategory.behavior: "سلوك",
    ParentNoteCategory.achievement: "إنجاز",
    ParentNoteCategory.warning: "تنبيه",
}

STATUS_LABELS_AR = {
    ParentNoteStatus.new: "جديد",
    ParentNoteStatus.read: "مقروء",
    ParentNoteStatus.replied: "تم الرد",
    ParentNoteStatus.closed: "مغلق",
}

PRIORITY_LABELS_AR = {
    ParentNotePriority.low: "منخفض",
    ParentNotePriority.medium: "متوسط",
    ParentNotePriority.high: "مرتفع",
    ParentNotePriority.urgent: "عاجل",
}

NOTIFICATION_TYPE_PARENT_NOTE = NotificationType.parent_note.value
NOTIFICATION_TYPE_PARENT_NOTE_READ = NotificationType.parent_note_read.value
NOTIFICATION_TYPE_PARENT_NOTE_REPLY = NotificationType.parent_note_reply.value


def category_label_ar(category: ParentNoteCategory | str) -> str:
    if isinstance(category, ParentNoteCategory):
        return CATEGORY_LABELS_AR.get(category, category.value)
    try:
        return CATEGORY_LABELS_AR.get(ParentNoteCategory(category), str(category))
    except ValueError:
        return str(category)


def status_label_ar(st: ParentNoteStatus | str) -> str:
    if isinstance(st, ParentNoteStatus):
        return STATUS_LABELS_AR.get(st, st.value)
    try:
        return STATUS_LABELS_AR.get(ParentNoteStatus(st), str(st))
    except ValueError:
        return str(st)


def priority_label_ar(pr: ParentNotePriority | str) -> str:
    if isinstance(pr, ParentNotePriority):
        return PRIORITY_LABELS_AR.get(pr, pr.value)
    try:
        return PRIORITY_LABELS_AR.get(ParentNotePriority(pr), str(pr))
    except ValueError:
        return str(pr)


def list_category_options() -> list[ParentNoteCategoryOptionOut]:
    return [
        ParentNoteCategoryOptionOut(value=cat, label_ar=CATEGORY_LABELS_AR[cat])
        for cat in ParentNoteCategory
    ]


def list_status_options() -> list[ParentNoteStatusOptionOut]:
    return [
        ParentNoteStatusOptionOut(value=st, label_ar=STATUS_LABELS_AR[st])
        for st in ParentNoteStatus
    ]


def list_priority_options() -> list[ParentNotePriorityOptionOut]:
    return [
        ParentNotePriorityOptionOut(value=pr, label_ar=PRIORITY_LABELS_AR[pr])
        for pr in ParentNotePriority
    ]


def _effective_status(
    note: StudentParentNote, *, read_count: int, reply_count: int
) -> ParentNoteStatus:
    if note.closed_at is not None:
        return ParentNoteStatus.closed
    if reply_count > 0:
        return ParentNoteStatus.replied
    if read_count > 0:
        return ParentNoteStatus.read
    return ParentNoteStatus.new


def _sync_note_status(note: StudentParentNote, *, read_count: int, reply_count: int) -> None:
    note.status = _effective_status(note, read_count=read_count, reply_count=reply_count)


async def _linked_parent_ids(db: AsyncSession, student_id: int) -> list[int]:
    result = await db.execute(
        select(ParentStudentLink.parent_id).where(ParentStudentLink.student_id == student_id)
    )
    return list(result.scalars().all())


async def _reads_for_notes(db: AsyncSession, note_ids: list[int]) -> dict[int, list[StudentParentNoteRead]]:
    if not note_ids:
        return {}
    result = await db.execute(
        select(StudentParentNoteRead).where(StudentParentNoteRead.note_id.in_(note_ids))
    )
    grouped: dict[int, list[StudentParentNoteRead]] = {}
    for row in result.scalars().all():
        grouped.setdefault(row.note_id, []).append(row)
    return grouped


async def _replies_for_notes(
    db: AsyncSession, note_ids: list[int]
) -> dict[int, list[StudentParentNoteReply]]:
    if not note_ids:
        return {}
    result = await db.execute(
        select(StudentParentNoteReply)
        .where(StudentParentNoteReply.note_id.in_(note_ids))
        .order_by(StudentParentNoteReply.created_at.asc())
    )
    grouped: dict[int, list[StudentParentNoteReply]] = {}
    for row in result.scalars().all():
        grouped.setdefault(row.note_id, []).append(row)
    return grouped


async def _reply_counts(db: AsyncSession, note_ids: list[int]) -> dict[int, int]:
    if not note_ids:
        return {}
    result = await db.execute(
        select(StudentParentNoteReply.note_id, func.count())
        .where(StudentParentNoteReply.note_id.in_(note_ids))
        .group_by(StudentParentNoteReply.note_id)
    )
    return {nid: int(cnt) for nid, cnt in result.all()}


async def _user_names(db: AsyncSession, user_ids: list[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    result = await db.execute(select(User.id, User.name).where(User.id.in_(user_ids)))
    return {uid: name for uid, name in result.all()}


async def _get_note_for_viewer(
    db: AsyncSession,
    note_id: int,
    viewer: User,
    *,
    student_id: int | None = None,
) -> StudentParentNote:
    note = await db.get(StudentParentNote, note_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملاحظة غير موجودة")
    if viewer.role == UserRole.parent:
        await resolve_parent_student_id(db, viewer, note.student_id)
    elif viewer.role == UserRole.teacher:
        sid = student_id or note.student_id
        await assert_student_in_teacher_scope(db, viewer, sid)
        if note.student_id != sid:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملاحظة غير موجودة")
    return note


def _reply_to_out(
    reply: StudentParentNoteReply,
    *,
    author_name: str,
    viewer: User | None,
) -> ParentNoteReplyOut:
    can_manage = viewer is not None and reply.author_id == viewer.id
    role = reply.author_role
    if isinstance(role, str):
        role = ParentNoteAuthorRole(role)
    return ParentNoteReplyOut(
        id=reply.id,
        note_id=reply.note_id,
        author_id=reply.author_id,
        author_name=author_name,
        author_role=role,
        body=reply.body,
        created_at=reply.created_at.isoformat() if reply.created_at else "",
        updated_at=reply.updated_at.isoformat() if reply.updated_at else "",
        can_edit=can_manage,
        can_delete=can_manage,
    )


async def _note_to_out(
    db: AsyncSession,
    note: StudentParentNote,
    *,
    reads: list[StudentParentNoteRead],
    replies: list[StudentParentNoteReply],
    reply_count: int,
    linked_parent_count: int,
    viewer: User | None = None,
    student_name: str | None = None,
    include_replies: bool = True,
) -> ParentNoteOut:
    parent_ids = [r.parent_id for r in reads]
    names = await _user_names(db, parent_ids)
    read_by = [
        ParentNoteReadByOut(
            parent_id=r.parent_id,
            parent_name=names.get(r.parent_id, "ولي أمر"),
            read_at=r.read_at.isoformat() if r.read_at else "",
        )
        for r in reads
    ]
    is_read = False
    read_at_viewer = None
    if viewer and viewer.role == UserRole.parent:
        for r in reads:
            if r.parent_id == viewer.id:
                is_read = True
                read_at_viewer = r.read_at.isoformat() if r.read_at else None
                break

    tp = await db.get(TeacherProfile, note.teacher_profile_id)
    author_name = "—"
    if tp:
        author = await db.get(User, tp.user_id)
        if author:
            author_name = author.name

    can_manage_note = False
    can_close = False
    if viewer and viewer.role == UserRole.teacher and tp:
        viewer_tp = await get_or_create_teacher_profile(db, viewer)
        can_manage_note = viewer_tp.id == note.teacher_profile_id
        can_close = can_manage_note and note.closed_at is None

    cat = note.category if isinstance(note.category, ParentNoteCategory) else ParentNoteCategory(note.category)
    st = _effective_status(note, read_count=len(reads), reply_count=reply_count)
    pr = note.priority if isinstance(note.priority, ParentNotePriority) else ParentNotePriority(note.priority)

    author_ids = [r.author_id for r in replies]
    reply_names = await _user_names(db, author_ids)
    reply_outs = [
        _reply_to_out(r, author_name=reply_names.get(r.author_id, "—"), viewer=viewer) for r in replies
    ]

    is_closed = note.closed_at is not None or st == ParentNoteStatus.closed
    can_reply = not is_closed

    return ParentNoteOut(
        id=note.id,
        student_id=note.student_id,
        student_name=student_name,
        title=note.title,
        description=note.description,
        category=cat,
        category_label_ar=category_label_ar(cat),
        status=st,
        status_label_ar=status_label_ar(st),
        priority=pr,
        priority_label_ar=priority_label_ar(pr),
        created_by_name=author_name,
        created_by_teacher_profile_id=note.teacher_profile_id,
        created_at=note.created_at.isoformat() if note.created_at else "",
        updated_at=note.updated_at.isoformat() if note.updated_at else "",
        is_read_by_viewer=is_read,
        read_at_by_viewer=read_at_viewer,
        parents_linked=linked_parent_count,
        parents_read_count=len(reads),
        read_by=read_by,
        reply_count=reply_count,
        replies=reply_outs if include_replies else [],
        is_closed=is_closed,
        closed_at=note.closed_at.isoformat() if note.closed_at else None,
        can_edit=can_manage_note,
        can_delete=can_manage_note,
        can_reply=can_reply,
        can_close=can_close,
    )


async def _notify_parents_new_note(
    db: AsyncSession,
    *,
    student_id: int,
    note_id: int,
    student_name: str,
) -> None:
    parent_ids = await _linked_parent_ids(db, student_id)
    for pid in parent_ids:
        await notification_service.create_notification(
            db,
            user_id=pid,
            notification_type=NOTIFICATION_TYPE_PARENT_NOTE,
            title="ملاحظة جديدة من المعلّم",
            body="New note from your teacher.",
            payload={"student_id": student_id, "note_id": note_id, "student_name": student_name},
        )


async def _notify_teacher_note_read(
    db: AsyncSession,
    *,
    note: StudentParentNote,
    parent: User,
    student_name: str,
) -> None:
    tp = await db.get(TeacherProfile, note.teacher_profile_id)
    if not tp:
        return
    await notification_service.create_notification(
        db,
        user_id=tp.user_id,
        notification_type=NOTIFICATION_TYPE_PARENT_NOTE_READ,
        title="تمت قراءة الملاحظة",
        body=f"قرأ ولي الأمر {parent.name} ملاحظة عن {student_name}.",
        payload={
            "student_id": note.student_id,
            "note_id": note.id,
            "parent_id": parent.id,
            "parent_name": parent.name,
        },
    )


async def _notify_reply(
    db: AsyncSession,
    *,
    note: StudentParentNote,
    replier: User,
    student_name: str,
) -> None:
    if replier.role == UserRole.parent:
        tp = await db.get(TeacherProfile, note.teacher_profile_id)
        if not tp:
            return
        await notification_service.create_notification(
            db,
            user_id=tp.user_id,
            notification_type=NOTIFICATION_TYPE_PARENT_NOTE_REPLY,
            title="رد من ولي الأمر",
            body="Parent replied to your note.",
            payload={
                "student_id": note.student_id,
                "note_id": note.id,
                "parent_id": replier.id,
                "parent_name": replier.name,
            },
        )
    elif replier.role == UserRole.teacher:
        parent_ids = await _linked_parent_ids(db, note.student_id)
        for pid in parent_ids:
            await notification_service.create_notification(
                db,
                user_id=pid,
                notification_type=NOTIFICATION_TYPE_PARENT_NOTE_REPLY,
                title="رد من المعلّم",
                body="Your teacher replied to a note.",
                payload={
                    "student_id": note.student_id,
                    "note_id": note.id,
                    "student_name": student_name,
                },
            )


async def _build_notes_list(
    db: AsyncSession,
    notes: list[StudentParentNote],
    *,
    viewer: User,
    student_name: str | None,
    linked_parent_count: int,
    include_replies: bool = False,
) -> list[ParentNoteOut]:
    note_ids = [n.id for n in notes]
    reads_map = await _reads_for_notes(db, note_ids)
    replies_map = await _replies_for_notes(db, note_ids) if include_replies else {}
    counts = await _reply_counts(db, note_ids)
    out: list[ParentNoteOut] = []
    for n in notes:
        reads = reads_map.get(n.id, [])
        out.append(
            await _note_to_out(
                db,
                n,
                reads=reads,
                replies=replies_map.get(n.id, []) if include_replies else [],
                reply_count=counts.get(n.id, 0),
                linked_parent_count=linked_parent_count,
                viewer=viewer,
                student_name=student_name,
                include_replies=include_replies,
            )
        )
    return out


async def list_teacher_parent_notes(
    db: AsyncSession,
    teacher: User,
    student_id: int,
    *,
    limit: int = 20,
) -> ParentNoteListOut:
    await assert_student_in_teacher_scope(db, teacher, student_id)
    student = await db.get(User, student_id)
    result = await db.execute(
        select(StudentParentNote)
        .where(StudentParentNote.student_id == student_id)
        .order_by(StudentParentNote.created_at.desc())
        .limit(min(limit, 50))
    )
    notes = list(result.scalars().all())
    linked = len(await _linked_parent_ids(db, student_id))
    out = await _build_notes_list(
        db,
        notes,
        viewer=teacher,
        student_name=student.name if student else None,
        linked_parent_count=linked,
        include_replies=False,
    )
    return ParentNoteListOut(notes=out, total=len(out), unread_count=0)


async def get_teacher_parent_note(
    db: AsyncSession,
    teacher: User,
    student_id: int,
    note_id: int,
) -> ParentNoteOut:
    note = await _get_note_for_viewer(db, note_id, teacher, student_id=student_id)
    student = await db.get(User, student_id)
    reads_map = await _reads_for_notes(db, [note.id])
    replies_map = await _replies_for_notes(db, [note.id])
    counts = await _reply_counts(db, [note.id])
    linked = len(await _linked_parent_ids(db, student_id))
    reads = reads_map.get(note.id, [])
    return await _note_to_out(
        db,
        note,
        reads=reads,
        replies=replies_map.get(note.id, []),
        reply_count=counts.get(note.id, 0),
        linked_parent_count=linked,
        viewer=teacher,
        student_name=student.name if student else None,
        include_replies=True,
    )


async def create_parent_note(
    db: AsyncSession,
    teacher: User,
    student_id: int,
    body: ParentNoteCreateIn,
) -> ParentNoteOut:
    await assert_student_in_teacher_scope(db, teacher, student_id)
    tp = await get_or_create_teacher_profile(db, teacher)
    student = await db.get(User, student_id)
    note = StudentParentNote(
        teacher_profile_id=tp.id,
        student_id=student_id,
        title=body.title.strip(),
        description=body.description.strip(),
        category=body.category,
        priority=body.priority,
        status=ParentNoteStatus.new,
    )
    db.add(note)
    await db.flush()
    await _notify_parents_new_note(
        db,
        student_id=student_id,
        note_id=note.id,
        student_name=student.name if student else "الطالب",
    )
    await db.commit()
    await db.refresh(note)
    linked = len(await _linked_parent_ids(db, student_id))
    return await _note_to_out(
        db,
        note,
        reads=[],
        replies=[],
        reply_count=0,
        linked_parent_count=linked,
        viewer=teacher,
        student_name=student.name if student else None,
    )


async def update_parent_note(
    db: AsyncSession,
    teacher: User,
    student_id: int,
    note_id: int,
    body: ParentNoteUpdateIn,
) -> ParentNoteOut:
    await assert_student_in_teacher_scope(db, teacher, student_id)
    tp = await get_or_create_teacher_profile(db, teacher)
    note = await db.scalar(
        select(StudentParentNote).where(
            StudentParentNote.id == note_id,
            StudentParentNote.student_id == student_id,
            StudentParentNote.teacher_profile_id == tp.id,
        )
    )
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملاحظة غير موجودة")
    if body.title is not None:
        note.title = body.title.strip()
    if body.description is not None:
        note.description = body.description.strip()
    if body.category is not None:
        note.category = body.category
    if body.priority is not None:
        note.priority = body.priority
    await db.commit()
    await db.refresh(note)
    return await get_teacher_parent_note(db, teacher, student_id, note_id)


async def delete_parent_note(
    db: AsyncSession,
    teacher: User,
    student_id: int,
    note_id: int,
) -> None:
    await assert_student_in_teacher_scope(db, teacher, student_id)
    tp = await get_or_create_teacher_profile(db, teacher)
    note = await db.scalar(
        select(StudentParentNote).where(
            StudentParentNote.id == note_id,
            StudentParentNote.student_id == student_id,
            StudentParentNote.teacher_profile_id == tp.id,
        )
    )
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملاحظة غير موجودة")
    await db.delete(note)
    await db.commit()


async def close_parent_note(
    db: AsyncSession,
    teacher: User,
    student_id: int,
    note_id: int,
) -> ParentNoteOut:
    await assert_student_in_teacher_scope(db, teacher, student_id)
    tp = await get_or_create_teacher_profile(db, teacher)
    note = await db.scalar(
        select(StudentParentNote).where(
            StudentParentNote.id == note_id,
            StudentParentNote.student_id == student_id,
            StudentParentNote.teacher_profile_id == tp.id,
        )
    )
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملاحظة غير موجودة")
    if note.closed_at is None:
        from datetime import datetime, timezone

        note.closed_at = datetime.now(timezone.utc)
        note.closed_by_user_id = teacher.id
        note.status = ParentNoteStatus.closed
    await db.commit()
    return await get_teacher_parent_note(db, teacher, student_id, note_id)


async def list_parent_viewer_notes(
    db: AsyncSession,
    parent: User,
    *,
    student_id: int | None = None,
    category: ParentNoteCategory | None = None,
    sort: str = "newest",
    limit: int = 30,
) -> ParentNoteListOut:
    sid = await resolve_parent_student_id(db, parent, student_id)
    q = select(StudentParentNote).where(StudentParentNote.student_id == sid)
    if category is not None:
        q = q.where(StudentParentNote.category == category)
    if sort == "oldest":
        q = q.order_by(StudentParentNote.created_at.asc())
    else:
        q = q.order_by(StudentParentNote.created_at.desc())
    q = q.limit(min(limit, 100))
    result = await db.execute(q)
    notes = list(result.scalars().all())
    student = await db.get(User, sid)
    out = await _build_notes_list(
        db,
        notes,
        viewer=parent,
        student_name=student.name if student else None,
        linked_parent_count=1,
        include_replies=False,
    )
    unread = sum(1 for row in out if not row.is_read_by_viewer)
    return ParentNoteListOut(notes=out, total=len(out), unread_count=unread)


async def get_parent_viewer_note(
    db: AsyncSession,
    parent: User,
    note_id: int,
) -> ParentNoteOut:
    note = await _get_note_for_viewer(db, note_id, parent)
    student = await db.get(User, note.student_id)
    reads_map = await _reads_for_notes(db, [note.id])
    replies_map = await _replies_for_notes(db, [note.id])
    counts = await _reply_counts(db, [note.id])
    reads = reads_map.get(note.id, [])
    return await _note_to_out(
        db,
        note,
        reads=reads,
        replies=replies_map.get(note.id, []),
        reply_count=counts.get(note.id, 0),
        linked_parent_count=1,
        viewer=parent,
        student_name=student.name if student else None,
        include_replies=True,
    )


async def parent_unread_count(
    db: AsyncSession,
    parent: User,
    *,
    student_id: int | None = None,
) -> int:
    sid = await resolve_parent_student_id(db, parent, student_id)
    total_notes = await db.scalar(
        select(func.count()).select_from(StudentParentNote).where(StudentParentNote.student_id == sid)
    )
    read_count = await db.scalar(
        select(func.count())
        .select_from(StudentParentNoteRead)
        .join(StudentParentNote, StudentParentNote.id == StudentParentNoteRead.note_id)
        .where(
            StudentParentNote.student_id == sid,
            StudentParentNoteRead.parent_id == parent.id,
        )
    )
    return max(0, int(total_notes or 0) - int(read_count or 0))


async def acknowledge_parent_note(
    db: AsyncSession,
    parent: User,
    note_id: int,
) -> ParentNoteOut:
    return await mark_parent_note_read(db, parent, note_id)


async def mark_parent_note_read(
    db: AsyncSession,
    parent: User,
    note_id: int,
) -> ParentNoteOut:
    note = await _get_note_for_viewer(db, note_id, parent)

    existing = await db.scalar(
        select(StudentParentNoteRead).where(
            StudentParentNoteRead.note_id == note_id,
            StudentParentNoteRead.parent_id == parent.id,
        )
    )
    if not existing:
        db.add(StudentParentNoteRead(note_id=note_id, parent_id=parent.id))
        await db.flush()
        student = await db.get(User, note.student_id)
        await _notify_teacher_note_read(
            db,
            note=note,
            parent=parent,
            student_name=student.name if student else "الطالب",
        )

    reads_map = await _reads_for_notes(db, [note.id])
    counts = await _reply_counts(db, [note.id])
    reads = reads_map.get(note.id, [])
    _sync_note_status(note, read_count=len(reads), reply_count=counts.get(note.id, 0))

    await db.commit()
    return await get_parent_viewer_note(db, parent, note_id)


async def create_note_reply(
    db: AsyncSession,
    viewer: User,
    note_id: int,
    body: ParentNoteReplyCreateIn,
    *,
    student_id: int | None = None,
) -> ParentNoteOut:
    note = await _get_note_for_viewer(db, note_id, viewer, student_id=student_id)
    if note.closed_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="الملاحظة مغلقة")

    if viewer.role == UserRole.teacher:
        role = ParentNoteAuthorRole.teacher
    elif viewer.role == UserRole.parent:
        role = ParentNoteAuthorRole.parent
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="غير مسموح")

    reply = StudentParentNoteReply(
        note_id=note_id,
        author_id=viewer.id,
        author_role=role,
        body=body.body.strip(),
    )
    db.add(reply)
    await db.flush()

    reads_map = await _reads_for_notes(db, [note.id])
    counts = await _reply_counts(db, [note.id])
    reads = reads_map.get(note.id, [])
    _sync_note_status(note, read_count=len(reads), reply_count=counts.get(note.id, 0))

    student = await db.get(User, note.student_id)
    await _notify_reply(
        db,
        note=note,
        replier=viewer,
        student_name=student.name if student else "الطالب",
    )
    await db.commit()

    if viewer.role == UserRole.teacher:
        return await get_teacher_parent_note(db, viewer, note.student_id, note_id)
    return await get_parent_viewer_note(db, viewer, note_id)


async def update_note_reply(
    db: AsyncSession,
    viewer: User,
    note_id: int,
    reply_id: int,
    body: ParentNoteReplyUpdateIn,
    *,
    student_id: int | None = None,
) -> ParentNoteOut:
    await _get_note_for_viewer(db, note_id, viewer, student_id=student_id)
    reply = await db.get(StudentParentNoteReply, reply_id)
    if not reply or reply.note_id != note_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الرد غير موجود")
    if reply.author_id != viewer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="لا يمكنك تعديل ردّ شخص آخر")

    reply.body = body.body.strip()
    await db.commit()

    if viewer.role == UserRole.teacher:
        sid = student_id or (await db.get(StudentParentNote, note_id)).student_id
        return await get_teacher_parent_note(db, viewer, sid, note_id)
    return await get_parent_viewer_note(db, viewer, note_id)


async def delete_note_reply(
    db: AsyncSession,
    viewer: User,
    note_id: int,
    reply_id: int,
    *,
    student_id: int | None = None,
) -> ParentNoteOut:
    note = await _get_note_for_viewer(db, note_id, viewer, student_id=student_id)
    reply = await db.get(StudentParentNoteReply, reply_id)
    if not reply or reply.note_id != note_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الرد غير موجود")
    if reply.author_id != viewer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="لا يمكنك حذف ردّ شخص آخر")

    await db.delete(reply)
    await db.flush()

    reads_map = await _reads_for_notes(db, [note.id])
    counts = await _reply_counts(db, [note.id])
    reads = reads_map.get(note.id, [])
    _sync_note_status(note, read_count=len(reads), reply_count=counts.get(note.id, 0))
    await db.commit()

    if viewer.role == UserRole.teacher:
        return await get_teacher_parent_note(db, viewer, note.student_id, note_id)
    return await get_parent_viewer_note(db, viewer, note_id)
