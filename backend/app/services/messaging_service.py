"""Internal messaging between teachers, students, and parents."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import Course, TeacherProfile
from app.models.conversation import (
    AttachmentKind,
    ConversationMessage,
    ConversationMessageAttachment,
    ConversationMessageRead,
    ConversationParticipant,
    ConversationParticipantRole,
    ConversationThread,
    ConversationThreadType,
    MessageDeliveryStatus,
    MessageKind,
)
from app.models.notification import NotificationType
from app.models.media import MediaAccessScope
from app.models.parent_link import ParentStudentLink
from app.models.user import User, UserRole
from app.schemas.messaging import (
    ConversationCreateIn,
    ConversationDetailOut,
    ConversationListOut,
    ConversationMessageOut,
    ConversationOut,
    ConversationParticipantOut,
    CourseMessageTeacherOut,
    MessageCreateIn,
    MessageSearchOut,
    MessagingContactOut,
    MessagingContactsOut,
    ParticipantSettingsIn,
    ThreadParticipantsUpdateIn,
)
from app.services import messaging_media_service, notification_service
from app.services.media_storage.upload import build_object_key, store_and_register_media
from app.services.parent_link_service import resolve_parent_student_id
from app.services.subscription_access_service import assert_student_active_enrollment
from app.services.teacher_student_service import assert_student_in_teacher_scope
from app.services.teacher_setup_service import get_or_create_teacher_profile
from app.utils.media_urls import teacher_avatar_url

NOTIFICATION_TYPE_MESSAGE = NotificationType.internal_message.value


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _user_names(db: AsyncSession, user_ids: list[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    result = await db.execute(select(User.id, User.name).where(User.id.in_(user_ids)))
    return {uid: name for uid, name in result.all()}


async def _teacher_profiles_for_users(
    db: AsyncSession, user_ids: list[int]
) -> dict[int, tuple[str | None, str | None]]:
    """user_id -> (display full_name, avatar_url)."""
    if not user_ids:
        return {}
    result = await db.execute(
        select(TeacherProfile.user_id, TeacherProfile.full_name, TeacherProfile.image_url).where(
            TeacherProfile.user_id.in_(user_ids)
        )
    )
    out: dict[int, tuple[str | None, str | None]] = {}
    for uid, full_name, image_url in result.all():
        name = (full_name or "").strip() or None
        out[uid] = (name, teacher_avatar_url(image_url))
    return out


async def _get_participant(
    db: AsyncSession, thread_id: int, user_id: int
) -> ConversationParticipant | None:
    return await db.scalar(
        select(ConversationParticipant).where(
            ConversationParticipant.thread_id == thread_id,
            ConversationParticipant.user_id == user_id,
        )
    )


async def _assert_participant(db: AsyncSession, thread_id: int, user: User) -> ConversationParticipant:
    row = await _get_participant(db, thread_id, user.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ليس لديك وصول لهذه المحادثة")
    thread = await db.get(ConversationThread, thread_id)
    if thread:
        allowed = await _allowed_student_ids_for_user(db, user)
        if allowed is not None and thread.student_id not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ليس لديك وصول لهذه المحادثة")
    return row


async def _parent_linked_to_student(db: AsyncSession, parent_id: int, student_id: int) -> bool:
    n = await db.scalar(
        select(func.count())
        .select_from(ParentStudentLink)
        .where(
            ParentStudentLink.parent_id == parent_id,
            ParentStudentLink.student_id == student_id,
        )
    )
    return int(n or 0) > 0


async def _assert_parent_child_access(db: AsyncSession, parent: User, student_id: int) -> None:
    await resolve_parent_student_id(db, parent, student_id)


async def _assert_student_self(db: AsyncSession, student: User, student_id: int) -> None:
    if student.id != student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="غير مسموح")


def _infer_thread_type(
    *, has_student: bool, parent_count: int
) -> ConversationThreadType:
    if has_student and parent_count > 0:
        return ConversationThreadType.teacher_student_parent
    if parent_count > 0:
        return ConversationThreadType.teacher_parent
    return ConversationThreadType.teacher_student


_ROLE_LABEL_AR: dict[ConversationParticipantRole, str] = {
    ConversationParticipantRole.teacher: "معلّم",
    ConversationParticipantRole.student: "طالب",
    ConversationParticipantRole.parent: "ولي أمر",
}


def _role_label(role: ConversationParticipantRole) -> str:
    if isinstance(role, str):
        role = ConversationParticipantRole(role)
    return _ROLE_LABEL_AR.get(role, role.value)


def _participant_display_name(role: ConversationParticipantRole, name: str) -> str:
    if isinstance(role, str):
        role = ConversationParticipantRole(role)
    clean = (name or "—").strip()
    if role == ConversationParticipantRole.teacher:
        if clean.startswith("الأستاذ "):
            return clean
        return f"الأستاذ {clean}"
    if role == ConversationParticipantRole.parent and not clean:
        return "ولي الأمر"
    return clean


def _is_stored_auto_title(title: str) -> bool:
    t = title.strip()
    return (
        t.startswith("محادثة مع ")
        or t.startswith("ولي أمر — ")
        or t.startswith("مجموعة — ")
        or " ↔ " in t
    )


def _conversation_pair_title(name_a: str, name_b: str) -> str:
    a = (name_a or "—").strip()
    b = (name_b or "—").strip()
    return f"{a} ↔ {b}"


def _conversation_kind_label(thread_type: ConversationThreadType) -> str | None:
    if isinstance(thread_type, str):
        thread_type = ConversationThreadType(thread_type)
    return {
        ConversationThreadType.teacher_student: "طالب",
        ConversationThreadType.teacher_parent: "ولي أمر",
        ConversationThreadType.teacher_student_parent: "مجموعة",
    }.get(thread_type)


def _participant_name_by_role(
    participants: list[tuple[int, str, ConversationParticipantRole]],
    role: ConversationParticipantRole,
) -> str | None:
    for _uid, name, part_role in participants:
        r = part_role if isinstance(part_role, ConversationParticipantRole) else ConversationParticipantRole(part_role)
        if r == role:
            return name
    return None


def _viewer_display_title(
    *,
    viewer_id: int,
    thread_type: ConversationThreadType,
    stored_title: str | None,
    participants: list[tuple[int, str, ConversationParticipantRole]],
) -> str:
    if isinstance(thread_type, str):
        thread_type = ConversationThreadType(thread_type)

    others = [(uid, name, role) for uid, name, role in participants if uid != viewer_id]

    if thread_type == ConversationThreadType.teacher_student_parent:
        if stored_title and not _is_stored_auto_title(stored_title):
            return stored_title.strip()
        labels = [_participant_display_name(role, name) for _, name, role in others]
        return " + ".join(labels) if labels else "مجموعة"

    if thread_type == ConversationThreadType.teacher_student:
        if stored_title and not _is_stored_auto_title(stored_title):
            return stored_title.strip()
        student_name = _participant_name_by_role(participants, ConversationParticipantRole.student)
        teacher_name = _participant_name_by_role(participants, ConversationParticipantRole.teacher)
        if student_name and teacher_name:
            return _conversation_pair_title(student_name, teacher_name)
        if len(others) == 1:
            _, name, role = others[0]
            return f"محادثة مع {_participant_display_name(role, name)}"
        return "محادثة"

    if thread_type == ConversationThreadType.teacher_parent:
        if stored_title and not _is_stored_auto_title(stored_title):
            return stored_title.strip()
        parent_name = _participant_name_by_role(participants, ConversationParticipantRole.parent)
        teacher_name = _participant_name_by_role(participants, ConversationParticipantRole.teacher)
        if parent_name and teacher_name:
            return _conversation_pair_title(parent_name, teacher_name)
        if len(others) == 1:
            _, name, role = others[0]
            return f"محادثة مع {_participant_display_name(role, name)}"
        return "محادثة"

    if stored_title:
        return stored_title.strip()
    return "محادثة"


def format_course_context_label(subject_name: str, grade: int) -> str:
    return f"{subject_name} — الصف {grade}"


async def _course_context_fields(
    db: AsyncSession, thread: ConversationThread
) -> tuple[int | None, str | None, str | None]:
    cid = getattr(thread, "course_id", None)
    if not cid:
        return None, None, None
    result = await db.execute(
        select(Course).where(Course.id == cid).options(selectinload(Course.subject))
    )
    course = result.scalar_one_or_none()
    if not course or not course.subject:
        return cid, None, None
    label = format_course_context_label(course.subject.name_ar, course.grade)
    return cid, label, course.subject.name_ar


async def _linked_parent_ids(db: AsyncSession, student_id: int) -> list[int]:
    result = await db.execute(
        select(ParentStudentLink.parent_id).where(ParentStudentLink.student_id == student_id)
    )
    return list(dict.fromkeys(result.scalars().all()))


async def _thread_participant_user_ids(db: AsyncSession, thread_id: int) -> set[int]:
    result = await db.execute(
        select(ConversationParticipant.user_id).where(
            ConversationParticipant.thread_id == thread_id
        )
    )
    return set(result.scalars().all())


async def _thread_has_teacher(db: AsyncSession, thread_id: int, teacher_id: int) -> bool:
    row = await db.scalar(
        select(ConversationParticipant.id).where(
            ConversationParticipant.thread_id == thread_id,
            ConversationParticipant.user_id == teacher_id,
            ConversationParticipant.role == ConversationParticipantRole.teacher,
        )
    )
    return row is not None


async def _thread_message_count(db: AsyncSession, thread_id: int) -> int:
    return int(
        await db.scalar(
            text("SELECT COUNT(*) FROM conversation_messages WHERE thread_id = :tid"),
            {"tid": thread_id},
        )
        or 0
    )


async def _thread_matches_participants(
    db: AsyncSession,
    thread_id: int,
    *,
    teacher_id: int,
    student_id: int,
    parent_ids: list[int],
) -> bool:
    target = {teacher_id, student_id, *parent_ids}
    users = await _thread_participant_user_ids(db, thread_id)
    if not await _thread_has_teacher(db, thread_id, teacher_id):
        return False
    if users == target:
        return True
    return not parent_ids and users == {teacher_id, student_id}


def _thread_rank_key(thread: ConversationThread, msg_count: int) -> tuple:
    ts = thread.last_message_at or thread.created_at
    return (msg_count, ts.timestamp() if ts else 0, thread.id)


async def _refresh_thread_preview(db: AsyncSession, thread: ConversationThread) -> None:
    row = await db.execute(
        text(
            """
            SELECT body, created_at FROM conversation_messages
            WHERE thread_id = :tid ORDER BY created_at DESC LIMIT 1
            """
        ),
        {"tid": thread.id},
    )
    last = row.first()
    if last:
        thread.last_message_preview = (last[0] or "")[:500]
        thread.last_message_at = last[1]


async def _merge_thread_into(db: AsyncSession, source_id: int, target_id: int) -> None:
    """Move messages from source to target and delete source thread."""
    if source_id == target_id:
        return
    await db.execute(
        text("UPDATE conversation_messages SET thread_id = :target WHERE thread_id = :source"),
        {"target": target_id, "source": source_id},
    )
    await db.execute(
        delete(ConversationParticipant).where(ConversationParticipant.thread_id == source_id)
    )
    await db.execute(delete(ConversationThread).where(ConversationThread.id == source_id))
    target = await db.get(ConversationThread, target_id)
    if target:
        await _refresh_thread_preview(db, target)


async def _reconcile_course_teacher_threads(
    db: AsyncSession,
    *,
    course_id: int,
    student_id: int,
    teacher_id: int,
    parent_ids: list[int],
) -> ConversationThread | None:
    """
    Single canonical thread for (teacher, student, course).

    Merges legacy course_id=NULL threads and empty course-scoped duplicates
    into the thread that actually has messages.
    """
    result = await db.execute(
        select(ConversationThread).where(ConversationThread.student_id == student_id)
    )
    candidates: list[ConversationThread] = []
    for thread in result.scalars().all():
        if thread.teacher_user_id and thread.teacher_user_id != teacher_id:
            continue
        if thread.teacher_user_id is None and not await _thread_has_teacher(db, thread.id, teacher_id):
            continue
        if not await _thread_matches_participants(
            db, thread.id, teacher_id=teacher_id, student_id=student_id, parent_ids=parent_ids
        ):
            continue
        if thread.course_id not in (None, course_id):
            continue
        candidates.append(thread)

    if not candidates:
        return None

    counts = {t.id: await _thread_message_count(db, t.id) for t in candidates}
    winner = max(candidates, key=lambda t: _thread_rank_key(t, counts[t.id]))

    for loser in candidates:
        if loser.id == winner.id:
            continue
        await _merge_thread_into(db, loser.id, winner.id)

    winner = await db.get(ConversationThread, winner.id)
    if not winner:
        return None
    winner.teacher_user_id = teacher_id
    winner.course_id = course_id
    await _refresh_thread_preview(db, winner)
    return winner


async def _find_existing_course_thread(
    db: AsyncSession,
    *,
    course_id: int,
    student_id: int,
    teacher_id: int,
    parent_ids: list[int] | None = None,
) -> ConversationThread | None:
    """Resolve the canonical thread for (student, course, teacher), including legacy rows."""
    return await _reconcile_course_teacher_threads(
        db,
        course_id=course_id,
        student_id=student_id,
        teacher_id=teacher_id,
        parent_ids=parent_ids or [],
    )


async def _resolve_course_teacher_thread(
    db: AsyncSession,
    *,
    course_id: int,
    student_id: int,
    teacher_id: int,
    parent_ids: list[int],
) -> ConversationThread | None:
    return await _reconcile_course_teacher_threads(
        db,
        course_id=course_id,
        student_id=student_id,
        teacher_id=teacher_id,
        parent_ids=parent_ids,
    )


async def _reconcile_legacy_teacher_student_threads(
    db: AsyncSession,
    *,
    student_id: int,
    teacher_id: int,
    parent_ids: list[int],
) -> ConversationThread | None:
    """Merge duplicate course_id=NULL threads for the same teacher+student."""
    result = await db.execute(
        select(ConversationThread).where(
            ConversationThread.student_id == student_id,
            ConversationThread.course_id.is_(None),
        )
    )
    candidates = []
    for thread in result.scalars().all():
        if not await _thread_matches_participants(
            db, thread.id, teacher_id=teacher_id, student_id=student_id, parent_ids=parent_ids
        ):
            continue
        candidates.append(thread)
    if not candidates:
        return None
    counts = {t.id: await _thread_message_count(db, t.id) for t in candidates}
    winner = max(candidates, key=lambda t: _thread_rank_key(t, counts[t.id]))
    for loser in candidates:
        if loser.id != winner.id:
            await _merge_thread_into(db, loser.id, winner.id)
    winner = await db.get(ConversationThread, winner.id)
    if winner:
        winner.teacher_user_id = teacher_id
    return winner


async def _assert_course_communication_allowed(
    db: AsyncSession, thread: ConversationThread, user: User
) -> None:
    """Students/parents may only message teachers for actively enrolled courses."""
    if user.role == UserRole.teacher or not thread.course_id or not thread.student_id:
        return
    if user.role in (UserRole.student, UserRole.parent):
        await assert_student_active_enrollment(db, thread.student_id, thread.course_id)


async def _load_course_for_student(
    db: AsyncSession, student_id: int, course_id: int
) -> tuple[Course, User]:
    from app.services.student_courses_service import get_student_profile

    profile = await get_student_profile(db, student_id)
    result = await db.execute(
        select(Course)
        .where(Course.id == course_id, Course.is_active.is_(True))
        .options(selectinload(Course.subject), selectinload(Course.teacher_profile))
    )
    course = result.scalar_one_or_none()
    if not course or not course.is_published or not course.teacher_profile.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الدورة غير متاحة")
    if profile.grade and course.grade != profile.grade:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="هذه المادة ليست لصفك")
    teacher_user = await db.get(User, course.teacher_profile.user_id)
    if not teacher_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المعلّم غير موجود")
    return course, teacher_user


def _default_title(
    *,
    thread_type: ConversationThreadType,
    student_name: str,
    teacher_name: str = "",
    parent_name: str = "",
    participant_names: list[str] | None = None,
) -> str:
    """Auto title persisted at thread creation."""
    if thread_type == ConversationThreadType.teacher_student:
        return _conversation_pair_title(student_name, teacher_name or "معلّم")
    if thread_type == ConversationThreadType.teacher_parent:
        parent = parent_name or (participant_names[0] if participant_names else "ولي أمر")
        return _conversation_pair_title(parent, teacher_name or "معلّم")
    return f"مجموعة — {student_name}"


async def _compute_sender_status(
    db: AsyncSession, message: ConversationMessage, thread_id: int
) -> MessageDeliveryStatus:
    others = await db.execute(
        select(ConversationParticipant.user_id).where(
            ConversationParticipant.thread_id == thread_id,
            ConversationParticipant.user_id != message.sender_id,
        )
    )
    other_ids = list(others.scalars().all())
    if not other_ids:
        return MessageDeliveryStatus.sent

    read_count = await db.scalar(
        select(func.count())
        .select_from(ConversationMessageRead)
        .where(
            ConversationMessageRead.message_id == message.id,
            ConversationMessageRead.user_id.in_(other_ids),
        )
    )
    if int(read_count or 0) >= len(other_ids):
        return MessageDeliveryStatus.read
    return MessageDeliveryStatus.delivered


def _message_kind_value(msg: ConversationMessage) -> MessageKind:
    raw = getattr(msg, "message_kind", None) or MessageKind.text.value
    try:
        return MessageKind(raw)
    except ValueError:
        return MessageKind.text



def _attachment_kind_for_message(kind: MessageKind) -> str:
    if kind == MessageKind.image:
        return AttachmentKind.image.value
    if kind == MessageKind.voice:
        return AttachmentKind.audio.value
    if kind in {MessageKind.pdf, MessageKind.document}:
        return AttachmentKind.document.value
    return AttachmentKind.file.value


def _storage_kind_for_message(kind: MessageKind) -> str:
    if kind == MessageKind.image:
        return "image"
    if kind == MessageKind.voice:
        return "audio"
    if kind == MessageKind.pdf:
        return "pdf"
    return "document"

async def _message_to_out(
    db: AsyncSession,
    msg: ConversationMessage,
    *,
    viewer_id: int,
    sender_names: dict[int, str],
    thread_id: int,
    sender_avatars: dict[int, str | None] | None = None,
) -> ConversationMessageOut:
    st = await _compute_sender_status(db, msg, thread_id)
    kind = _message_kind_value(msg)
    deleted = msg.deleted_at is not None
    body = "تم حذف الرسالة" if deleted else (msg.body or "")
    avatars = sender_avatars or {}
    linked_attachment = await db.scalar(
        select(ConversationMessageAttachment)
        .where(ConversationMessageAttachment.message_id == msg.id)
        .options(selectinload(ConversationMessageAttachment.media_object))
        .order_by(ConversationMessageAttachment.sort_order, ConversationMessageAttachment.id)
        .limit(1)
    )
    linked_media = linked_attachment.media_object if linked_attachment else None
    attachment_media_id = linked_attachment.media_object_id if linked_attachment and not deleted else None
    attachment_url = None
    attachment_name = msg.attachment_name
    attachment_mime = msg.attachment_mime
    voice_duration_ms = msg.voice_duration_ms
    if not deleted and linked_attachment:
        attachment_url = f"/api/media/{linked_attachment.media_object_id}/download-url"
        attachment_name = linked_attachment.display_name or attachment_name
        attachment_mime = (linked_media.mime_type if linked_media else None) or attachment_mime
        voice_duration_ms = linked_attachment.voice_duration_ms or voice_duration_ms
    elif not deleted:
        attachment_url = msg.attachment_url

    return ConversationMessageOut(
        id=msg.id,
        thread_id=msg.thread_id,
        sender_id=msg.sender_id,
        sender_name=sender_names.get(msg.sender_id, "—"),
        sender_avatar_url=avatars.get(msg.sender_id),
        body=body,
        message_kind=kind,
        attachment_media_id=attachment_media_id,
        attachment_url=attachment_url,
        attachment_name=attachment_name,
        attachment_mime=attachment_mime,
        voice_duration_ms=voice_duration_ms,
        is_deleted=deleted,
        status=st,
        created_at=msg.created_at.isoformat() if msg.created_at else "",
        is_mine=msg.sender_id == viewer_id,
    )


async def _notify_message_recipients(
    db: AsyncSession,
    *,
    thread_id: int,
    sender: User,
    message_id: int,
    preview_text: str,
) -> None:
    others = await db.execute(
        select(ConversationParticipant.user_id).where(
            ConversationParticipant.thread_id == thread_id,
            ConversationParticipant.user_id != sender.id,
        )
    )
    sender_name = sender.name or "مستخدم"
    snippet = (preview_text or "").strip()[:120]
    body = f"{sender_name}: {snippet}" if snippet else f"رسالة جديدة من {sender_name}"
    for uid in others.scalars().all():
        await notification_service.create_notification(
            db,
            user_id=uid,
            notification_type=NOTIFICATION_TYPE_MESSAGE,
            title="رسالة جديدة",
            body=body,
            payload={"thread_id": thread_id, "message_id": message_id},
        )


async def _unread_for_participant(
    db: AsyncSession, thread_id: int, participant: ConversationParticipant
) -> int:
    q = select(func.count()).select_from(ConversationMessage).where(
        ConversationMessage.thread_id == thread_id,
        ConversationMessage.sender_id != participant.user_id,
    )
    if participant.last_read_at:
        q = q.where(ConversationMessage.created_at > participant.last_read_at)
    return int(await db.scalar(q) or 0)


async def _thread_to_out(
    db: AsyncSession,
    thread: ConversationThread,
    viewer: User,
    *,
    participant_row: ConversationParticipant,
    include_messages: bool = False,
    message_limit: int = 80,
) -> ConversationOut | ConversationDetailOut:
    parts = await db.execute(
        select(ConversationParticipant).where(ConversationParticipant.thread_id == thread.id)
    )
    part_rows = list(parts.scalars().all())
    user_ids = [p.user_id for p in part_rows]
    names = await _user_names(db, user_ids)
    teacher_user_ids = [
        p.user_id
        for p in part_rows
        if (
            p.role if isinstance(p.role, ConversationParticipantRole) else ConversationParticipantRole(p.role)
        )
        == ConversationParticipantRole.teacher
    ]
    teacher_profiles = await _teacher_profiles_for_users(db, teacher_user_ids)
    student = await db.get(User, thread.student_id)

    thread_type = (
        thread.thread_type
        if isinstance(thread.thread_type, ConversationThreadType)
        else ConversationThreadType(thread.thread_type)
    )
    participant_tuples: list[tuple[int, str, ConversationParticipantRole]] = []
    participants_out: list[ConversationParticipantOut] = []
    for p in part_rows:
        role = p.role if isinstance(p.role, ConversationParticipantRole) else ConversationParticipantRole(p.role)
        profile_name, avatar_url = teacher_profiles.get(p.user_id, (None, None))
        raw_name = profile_name or names.get(p.user_id, "—")
        participant_tuples.append((p.user_id, raw_name, role))
        participants_out.append(
            ConversationParticipantOut(
                user_id=p.user_id,
                name=raw_name,
                role=role,
                display_name=_participant_display_name(role, raw_name),
                role_label=_role_label(role),
                avatar_url=avatar_url if role == ConversationParticipantRole.teacher else None,
            )
        )

    other_participants = [p for p in participants_out if p.user_id != viewer.id]
    unread = await _unread_for_participant(db, thread.id, participant_row)
    title = _viewer_display_title(
        viewer_id=viewer.id,
        thread_type=thread_type,
        stored_title=thread.title,
        participants=participant_tuples,
    )

    course_id, course_label, course_subject = await _course_context_fields(db, thread)

    base = ConversationOut(
        id=thread.id,
        title=title,
        thread_type=thread_type,
        conversation_kind_label=_conversation_kind_label(thread_type),
        student_id=thread.student_id,
        student_name=student.name if student else None,
        course_id=course_id,
        course_context_label=course_label,
        course_subject_name=course_subject,
        include_parent=bool(getattr(thread, "include_parent", False)),
        participants=participants_out,
        other_participants=other_participants,
        last_message_preview=thread.last_message_preview,
        last_message_at=thread.last_message_at.isoformat() if thread.last_message_at else None,
        unread_count=unread,
        is_pinned=bool(getattr(participant_row, "is_pinned", False)),
        is_archived=bool(getattr(participant_row, "is_archived", False)),
        created_at=thread.created_at.isoformat() if thread.created_at else "",
    )

    if not include_messages:
        return base

    msg_result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.thread_id == thread.id)
        .order_by(ConversationMessage.created_at.asc())
        .limit(message_limit)
    )
    messages = list(msg_result.scalars().all())
    sender_ids = list({m.sender_id for m in messages})
    sender_names = await _user_names(db, sender_ids)
    teacher_senders = [
        sid
        for sid in sender_ids
        if any(p.user_id == sid and p.role == ConversationParticipantRole.teacher for p in participants_out)
    ]
    teacher_sender_profiles = await _teacher_profiles_for_users(db, teacher_senders)
    sender_avatars = {uid: avatar for uid, (_, avatar) in teacher_sender_profiles.items()}
    for p in participants_out:
        if p.role == ConversationParticipantRole.teacher and p.avatar_url:
            sender_avatars.setdefault(p.user_id, p.avatar_url)
    msg_out = [
        await _message_to_out(
            db,
            m,
            viewer_id=viewer.id,
            sender_names=sender_names,
            thread_id=thread.id,
            sender_avatars=sender_avatars,
        )
        for m in messages
    ]

    return ConversationDetailOut(**base.model_dump(), messages=msg_out)


async def _allowed_student_ids_for_user(db: AsyncSession, user: User) -> set[int] | None:
    """None = no extra filter (teacher). Set = threads must match student_id in set."""
    if user.role == UserRole.student:
        return {user.id}
    if user.role == UserRole.parent:
        result = await db.execute(
            select(ParentStudentLink.student_id).where(ParentStudentLink.parent_id == user.id)
        )
        return set(result.scalars().all())
    return None


async def list_conversations(
    db: AsyncSession, user: User, *, include_archived: bool = False
) -> ConversationListOut:
    part_q = await db.execute(
        select(ConversationParticipant).where(ConversationParticipant.user_id == user.id)
    )
    my_parts = {p.thread_id: p for p in part_q.scalars().all()}
    if not my_parts:
        return ConversationListOut()

    allowed_students = await _allowed_student_ids_for_user(db, user)
    thread_ids = list(my_parts.keys())
    result = await db.execute(
        select(ConversationThread)
        .where(ConversationThread.id.in_(thread_ids))
        .order_by(ConversationThread.last_message_at.desc().nullslast(), ConversationThread.id.desc())
    )
    threads = list(result.scalars().all())
    if allowed_students is not None:
        threads = [t for t in threads if t.student_id in allowed_students]
    if not include_archived:
        threads = [t for t in threads if not getattr(my_parts.get(t.id), "is_archived", False)]

    def _sort_key(t: ConversationThread) -> tuple:
        p = my_parts[t.id]
        ts = t.last_message_at or t.created_at or datetime.min.replace(tzinfo=timezone.utc)
        return (getattr(p, "is_pinned", False), ts)

    threads.sort(key=_sort_key, reverse=True)

    out: list[ConversationOut] = []
    total_unread = 0
    for t in threads:
        row = await _thread_to_out(db, t, user, participant_row=my_parts[t.id])
        out.append(row)
        total_unread += row.unread_count
    return ConversationListOut(conversations=out, total_unread=total_unread)


async def get_conversation(
    db: AsyncSession, user: User, thread_id: int, *, mark_read: bool = True
) -> ConversationDetailOut:
    participant = await _assert_participant(db, thread_id, user)
    thread = await db.get(ConversationThread, thread_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة غير موجودة")

    if mark_read:
        await mark_thread_read(db, user, thread_id)
        await db.commit()

    participant = await _get_participant(db, thread_id, user.id) or participant
    detail = await _thread_to_out(
        db, thread, user, participant_row=participant, include_messages=True
    )
    return detail


async def total_unread_count(db: AsyncSession, user: User) -> int:
    data = await list_conversations(db, user)
    return data.total_unread


async def create_conversation(
    db: AsyncSession, teacher: User, body: ConversationCreateIn
) -> ConversationDetailOut:
    if teacher.role != UserRole.teacher:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="إنشاء المحادثات للمعلمين فقط")

    student = await assert_student_in_teacher_scope(db, teacher, body.student_id)
    parent_ids = list(dict.fromkeys(body.parent_ids or []))

    for pid in parent_ids:
        parent = await db.get(User, pid)
        if not parent or parent.role != UserRole.parent:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ولي أمر غير صالح")
        if not await _parent_linked_to_student(db, pid, body.student_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ولي الأمر غير مرتبط بهذا الطالب",
            )

    if not body.include_student and not parent_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اختر مشاركاً واحداً على الأقل")

    thread_type = _infer_thread_type(has_student=body.include_student, parent_count=len(parent_ids))

    if body.include_student and not parent_ids:
        reconciled = await _reconcile_legacy_teacher_student_threads(
            db,
            student_id=body.student_id,
            teacher_id=teacher.id,
            parent_ids=[],
        )
        if reconciled:
            return await get_conversation(db, teacher, reconciled.id, mark_read=False)
        course_rows = await db.execute(
            select(ConversationThread.course_id)
            .where(
                ConversationThread.student_id == body.student_id,
                ConversationThread.course_id.isnot(None),
            )
            .distinct()
        )
        for (cid,) in course_rows.all():
            if cid is None:
                continue
            merged = await _reconcile_course_teacher_threads(
                db,
                course_id=cid,
                student_id=body.student_id,
                teacher_id=teacher.id,
                parent_ids=[],
            )
            if merged:
                return await get_conversation(db, teacher, merged.id, mark_read=False)

    existing = await _find_existing_thread(
        db,
        teacher_id=teacher.id,
        student_id=body.student_id,
        include_student=body.include_student,
        parent_ids=parent_ids,
    )
    if existing:
        if not existing.teacher_user_id:
            existing.teacher_user_id = teacher.id
        return await get_conversation(db, teacher, existing.id, mark_read=False)

    thread = ConversationThread(
        title=body.title.strip() if body.title else None,
        thread_type=thread_type,
        student_id=body.student_id,
        teacher_user_id=teacher.id,
        created_by_user_id=teacher.id,
    )
    db.add(thread)
    await db.flush()

    db.add(
        ConversationParticipant(
            thread_id=thread.id,
            user_id=teacher.id,
            role=ConversationParticipantRole.teacher,
            last_read_at=_now(),
        )
    )
    if body.include_student:
        db.add(
            ConversationParticipant(
                thread_id=thread.id,
                user_id=student.id,
                role=ConversationParticipantRole.student,
            )
        )
    for pid in parent_ids:
        db.add(
            ConversationParticipant(
                thread_id=thread.id,
                user_id=pid,
                role=ConversationParticipantRole.parent,
            )
        )

    if not thread.title:
        names = await _user_names(
            db,
            [teacher.id, student.id, *parent_ids],
        )
        thread.title = _default_title(
            thread_type=thread_type,
            student_name=names.get(student.id, student.name),
            teacher_name=names.get(teacher.id, teacher.name),
            parent_name=names.get(parent_ids[0], "") if parent_ids else "",
            participant_names=[names.get(pid, "") for pid in parent_ids],
        )

    await db.commit()
    await db.refresh(thread)
    return await get_conversation(db, teacher, thread.id, mark_read=False)


async def _find_existing_thread(
    db: AsyncSession,
    *,
    teacher_id: int,
    student_id: int,
    include_student: bool,
    parent_ids: list[int],
) -> ConversationThread | None:
    """Reuse thread with identical participant set (prefer thread with messages)."""
    target = {teacher_id}
    if include_student:
        target.add(student_id)
    target.update(parent_ids)

    result = await db.execute(
        select(ConversationThread).where(ConversationThread.student_id == student_id)
    )
    matches: list[ConversationThread] = []
    for thread in result.scalars().all():
        users = await _thread_participant_user_ids(db, thread.id)
        if users == target:
            matches.append(thread)
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    counts = {t.id: await _thread_message_count(db, t.id) for t in matches}
    return max(matches, key=lambda t: _thread_rank_key(t, counts[t.id]))


async def send_message(
    db: AsyncSession, user: User, thread_id: int, body: MessageCreateIn
) -> ConversationDetailOut:
    await _assert_participant(db, thread_id, user)
    thread = await db.get(ConversationThread, thread_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة غير موجودة")
    await _assert_course_communication_allowed(db, thread, user)

    text = body.body.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="نص الرسالة مطلوب")
    msg = ConversationMessage(
        thread_id=thread_id,
        sender_id=user.id,
        body=text,
        message_kind=MessageKind.text.value,
        status=MessageDeliveryStatus.delivered,
    )
    db.add(msg)
    await db.flush()

    thread.last_message_at = msg.created_at or _now()
    thread.last_message_preview = text[:500]
    participant = await _get_participant(db, thread_id, user.id)
    if participant:
        participant.last_read_at = msg.created_at or _now()

    await _notify_message_recipients(
        db, thread_id=thread_id, sender=user, message_id=msg.id, preview_text=text
    )

    if user.role == UserRole.student:
        from app.models.student_activity_tracking import EngagementEventType
        from app.services import student_activity_tracking_service

        await student_activity_tracking_service.record_engagement_event(
            db,
            user.id,
            EngagementEventType.messaging_activity,
            resource_type="thread",
            resource_id=thread_id,
            metadata={"message_id": msg.id},
        )

    await db.commit()
    return await get_conversation(db, user, thread_id, mark_read=False)


async def mark_message_read(db: AsyncSession, user: User, message_id: int) -> ConversationMessageOut:
    msg = await db.get(ConversationMessage, message_id)
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الرسالة غير موجودة")
    await _assert_participant(db, msg.thread_id, user)
    if msg.sender_id == user.id:
        st = await _compute_sender_status(db, msg, msg.thread_id)
        sender_names = await _user_names(db, [msg.sender_id])
        return ConversationMessageOut(
            id=msg.id,
            thread_id=msg.thread_id,
            sender_id=msg.sender_id,
            sender_name=sender_names.get(msg.sender_id, "—"),
            body=msg.body,
            status=st,
            created_at=msg.created_at.isoformat() if msg.created_at else "",
            is_mine=True,
        )

    existing = await db.scalar(
        select(ConversationMessageRead).where(
            ConversationMessageRead.message_id == message_id,
            ConversationMessageRead.user_id == user.id,
        )
    )
    if not existing:
        db.add(ConversationMessageRead(message_id=message_id, user_id=user.id))
        participant = await _get_participant(db, msg.thread_id, user.id)
        if participant and (not participant.last_read_at or (msg.created_at and msg.created_at > participant.last_read_at)):
            participant.last_read_at = msg.created_at or _now()

    await db.flush()
    await _refresh_message_statuses(db, msg.thread_id)
    await db.commit()

    st = await _compute_sender_status(db, msg, msg.thread_id)
    sender_names = await _user_names(db, [msg.sender_id])
    return ConversationMessageOut(
        id=msg.id,
        thread_id=msg.thread_id,
        sender_id=msg.sender_id,
        sender_name=sender_names.get(msg.sender_id, "—"),
        body=msg.body,
        status=st,
        created_at=msg.created_at.isoformat() if msg.created_at else "",
        is_mine=msg.sender_id == user.id,
    )


async def mark_thread_read(db: AsyncSession, user: User, thread_id: int) -> None:
    participant = await _assert_participant(db, thread_id, user)
    now = _now()
    participant.last_read_at = now

    others_msgs = await db.execute(
        select(ConversationMessage).where(
            ConversationMessage.thread_id == thread_id,
            ConversationMessage.sender_id != user.id,
        )
    )
    for msg in others_msgs.scalars().all():
        exists = await db.scalar(
            select(ConversationMessageRead).where(
                ConversationMessageRead.message_id == msg.id,
                ConversationMessageRead.user_id == user.id,
            )
        )
        if not exists:
            db.add(ConversationMessageRead(message_id=msg.id, user_id=user.id))

    await _refresh_message_statuses(db, thread_id)
    await db.flush()


async def _refresh_message_statuses(db: AsyncSession, thread_id: int) -> None:
    result = await db.execute(
        select(ConversationMessage).where(ConversationMessage.thread_id == thread_id)
    )
    for msg in result.scalars().all():
        msg.status = await _compute_sender_status(db, msg, thread_id)


async def list_teacher_contacts(db: AsyncSession, teacher: User) -> MessagingContactsOut:
    from app.services.teacher_student_service import search_teacher_students

    search = await search_teacher_students(db, teacher)
    students_out: list[MessagingContactOut] = []
    parents_out: list[MessagingContactOut] = []

    for row in search.students:
        sid = row.student_id
        sname = row.full_name
        students_out.append(
            MessagingContactOut(
                user_id=sid,
                name=sname,
                role="student",
                student_id=sid,
                student_name=sname,
            )
        )
        links = await db.execute(
            select(ParentStudentLink.parent_id).where(ParentStudentLink.student_id == sid)
        )
        parent_ids = list(links.scalars().all())
        if parent_ids:
            names = await _user_names(db, parent_ids)
            for pid in parent_ids:
                parents_out.append(
                    MessagingContactOut(
                        user_id=pid,
                        name=names.get(pid, "ولي أمر"),
                        role="parent",
                        student_id=sid,
                        student_name=sname,
                    )
                )

    seen = set()
    unique_parents = []
    for p in parents_out:
        key = (p.user_id, p.student_id)
        if key not in seen:
            seen.add(key)
            unique_parents.append(p)

    return MessagingContactsOut(students=students_out, parents=unique_parents)


async def update_participant_settings(
    db: AsyncSession, user: User, thread_id: int, body: ParticipantSettingsIn
) -> ConversationOut:
    participant = await _assert_participant(db, thread_id, user)
    if body.is_pinned is not None:
        participant.is_pinned = body.is_pinned
    if body.is_archived is not None:
        participant.is_archived = body.is_archived
    await db.commit()
    thread = await db.get(ConversationThread, thread_id)
    participant = await _get_participant(db, thread_id, user.id)
    return await _thread_to_out(db, thread, user, participant_row=participant)


async def mark_thread_unread(db: AsyncSession, user: User, thread_id: int) -> ConversationOut:
    participant = await _assert_participant(db, thread_id, user)
    participant.last_read_at = None
    await db.commit()
    thread = await db.get(ConversationThread, thread_id)
    participant = await _get_participant(db, thread_id, user.id)
    return await _thread_to_out(db, thread, user, participant_row=participant)


async def delete_message(db: AsyncSession, user: User, message_id: int) -> ConversationMessageOut:
    msg = await db.get(ConversationMessage, message_id)
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الرسالة غير موجودة")
    if msg.sender_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="يمكنك حذف رسائلك فقط")
    await _assert_participant(db, msg.thread_id, user)
    msg.deleted_at = _now()
    msg.body = ""
    await db.commit()
    sender_names = await _user_names(db, [msg.sender_id])
    avatars = {
        uid: av
        for uid, (_, av) in (await _teacher_profiles_for_users(db, [msg.sender_id])).items()
    }
    return await _message_to_out(
        db,
        msg,
        viewer_id=user.id,
        sender_names=sender_names,
        thread_id=msg.thread_id,
        sender_avatars=avatars,
    )


async def search_messages(
    db: AsyncSession, user: User, thread_id: int, *, query: str, limit: int = 50
) -> MessageSearchOut:
    await _assert_participant(db, thread_id, user)
    q = query.strip()
    if not q:
        return MessageSearchOut(messages=[], query=q)
    pattern = f"%{q}%"
    result = await db.execute(
        select(ConversationMessage)
        .where(
            ConversationMessage.thread_id == thread_id,
            ConversationMessage.deleted_at.is_(None),
            ConversationMessage.body.ilike(pattern),
        )
        .order_by(ConversationMessage.created_at.desc())
        .limit(min(limit, 100))
    )
    messages = list(result.scalars().all())
    sender_ids = list({m.sender_id for m in messages})
    sender_names = await _user_names(db, sender_ids)
    avatars = {
        uid: av
        for uid, (_, av) in (await _teacher_profiles_for_users(db, sender_ids)).items()
    }
    out = [
        await _message_to_out(
            db,
            m,
            viewer_id=user.id,
            sender_names=sender_names,
            thread_id=thread_id,
            sender_avatars=avatars,
        )
        for m in reversed(messages)
    ]
    return MessageSearchOut(messages=out, query=q)


async def send_message_with_attachment(
    db: AsyncSession,
    user: User,
    thread_id: int,
    *,
    file_content: bytes,
    filename: str,
    mime_type: str,
    caption: str = "",
    voice_duration_ms: int | None = None,
) -> ConversationDetailOut:
    await _assert_participant(db, thread_id, user)
    thread = await db.get(ConversationThread, thread_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة غير موجودة")
    await _assert_course_communication_allowed(db, thread, user)

    kind, stored_name, mime = messaging_media_service.prepare_message_file(
        content=file_content,
        filename=filename,
        mime_type=mime_type,
        voice_duration_ms=voice_duration_ms,
    )
    stored = await store_and_register_media(
        db,
        content=file_content,
        filename=stored_name,
        mime_type=mime,
        uploaded_by_user_id=user.id,
        access_scope=MediaAccessScope.private.value,
        object_key=build_object_key("messages", f"thread_{thread_id}", filename=stored_name),
        kind=_storage_kind_for_message(kind),
        metadata_json={
            "domain": "messaging",
            "thread_id": thread_id,
            "owner_user_id": user.id,
            "message_kind": kind.value,
        },
    )
    text = caption.strip()
    if not text:
        text = messaging_media_service.preview_label_for_kind(kind, stored_name)

    msg = ConversationMessage(
        thread_id=thread_id,
        sender_id=user.id,
        body=text,
        message_kind=kind.value,
        attachment_url=stored.client_url,
        attachment_name=stored_name,
        attachment_mime=stored.mime_type,
        voice_duration_ms=voice_duration_ms if kind == MessageKind.voice else None,
        status=MessageDeliveryStatus.delivered,
    )
    db.add(msg)
    await db.flush()

    if isinstance(stored.media.metadata_json, dict):
        stored.media.metadata_json = {**stored.media.metadata_json, "message_id": msg.id}
    db.add(
        ConversationMessageAttachment(
            message_id=msg.id,
            media_object_id=stored.media.id,
            attachment_kind=_attachment_kind_for_message(kind),
            display_name=stored_name,
            voice_duration_ms=voice_duration_ms if kind == MessageKind.voice else None,
        )
    )
    await db.flush()

    preview = messaging_media_service.preview_label_for_kind(kind, stored_name)
    if text and text != preview:
        preview = f"{preview} — {text[:80]}"

    thread.last_message_at = msg.created_at or _now()
    thread.last_message_preview = preview[:500]
    participant = await _get_participant(db, thread_id, user.id)
    if participant:
        participant.last_read_at = msg.created_at or _now()

    await _notify_message_recipients(
        db, thread_id=thread_id, sender=user, message_id=msg.id, preview_text=preview
    )
    await db.commit()
    return await get_conversation(db, user, thread_id, mark_read=False)


async def _sync_thread_type(db: AsyncSession, thread: ConversationThread) -> None:
    parts = await db.execute(
        select(ConversationParticipant).where(ConversationParticipant.thread_id == thread.id)
    )
    rows = list(parts.scalars().all())
    has_student = any(
        (p.role if isinstance(p.role, ConversationParticipantRole) else ConversationParticipantRole(p.role))
        == ConversationParticipantRole.student
        for p in rows
    )
    parent_count = sum(
        1
        for p in rows
        if (p.role if isinstance(p.role, ConversationParticipantRole) else ConversationParticipantRole(p.role))
        == ConversationParticipantRole.parent
    )
    thread.thread_type = _infer_thread_type(has_student=has_student, parent_count=parent_count)


async def update_thread_participants(
    db: AsyncSession, teacher: User, thread_id: int, body: ThreadParticipantsUpdateIn
) -> ConversationDetailOut:
    if teacher.role != UserRole.teacher:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="للمعلمين فقط")
    await _assert_participant(db, thread_id, teacher)
    thread = await db.get(ConversationThread, thread_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة غير موجودة")

    student = await assert_student_in_teacher_scope(db, teacher, thread.student_id)

    for pid in body.remove_parent_ids or []:
        row = await db.scalar(
            select(ConversationParticipant).where(
                ConversationParticipant.thread_id == thread_id,
                ConversationParticipant.user_id == pid,
                ConversationParticipant.role == ConversationParticipantRole.parent,
            )
        )
        if row:
            await db.delete(row)

    for pid in body.add_parent_ids or []:
        parent = await db.get(User, pid)
        if not parent or parent.role != UserRole.parent:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ولي أمر غير صالح")
        if not await _parent_linked_to_student(db, pid, thread.student_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ولي الأمر غير مرتبط بالطالب")
        exists = await _get_participant(db, thread_id, pid)
        if not exists:
            db.add(
                ConversationParticipant(
                    thread_id=thread_id,
                    user_id=pid,
                    role=ConversationParticipantRole.parent,
                )
            )

    if body.include_student is True:
        exists = await _get_participant(db, thread_id, student.id)
        if not exists:
            db.add(
                ConversationParticipant(
                    thread_id=thread_id,
                    user_id=student.id,
                    role=ConversationParticipantRole.student,
                )
            )

    await _sync_thread_type(db, thread)
    await db.commit()
    return await get_conversation(db, teacher, thread_id, mark_read=False)


async def open_course_teacher_conversation(
    db: AsyncSession,
    student: User,
    course_id: int,
    *,
    include_parent: bool = False,
) -> CourseMessageTeacherOut:
    """Open or create a course-scoped thread between student and course teacher."""
    if student.role != UserRole.student:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="للطلاب فقط")

    await assert_student_active_enrollment(db, student.id, course_id)
    course, teacher = await _load_course_for_student(db, student.id, course_id)
    label = format_course_context_label(course.subject.name_ar, course.grade)
    parent_ids = await _linked_parent_ids(db, student.id) if include_parent else []

    existing = await _reconcile_course_teacher_threads(
        db,
        course_id=course_id,
        student_id=student.id,
        teacher_id=teacher.id,
        parent_ids=parent_ids,
    )
    if existing:
        if include_parent and parent_ids:
            existing.include_parent = True
            for pid in parent_ids:
                parent = await db.get(User, pid)
                if not parent or parent.role != UserRole.parent:
                    continue
                if not await _parent_linked_to_student(db, pid, student.id):
                    continue
                if not await _get_participant(db, existing.id, pid):
                    db.add(
                        ConversationParticipant(
                            thread_id=existing.id,
                            user_id=pid,
                            role=ConversationParticipantRole.parent,
                        )
                    )
            await _sync_thread_type(db, existing)
        await db.commit()
        return CourseMessageTeacherOut(
            thread_id=existing.id, created=False, course_context_label=label
        )

    thread_type = _infer_thread_type(has_student=True, parent_count=len(parent_ids))
    thread = ConversationThread(
        thread_type=thread_type,
        student_id=student.id,
        teacher_user_id=teacher.id,
        course_id=course_id,
        include_parent=include_parent,
        created_by_user_id=student.id,
    )
    db.add(thread)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        existing = await _resolve_course_teacher_thread(
            db,
            course_id=course_id,
            student_id=student.id,
            teacher_id=teacher.id,
            parent_ids=parent_ids,
        )
        if not existing:
            raise
        if not existing.course_id:
            existing.course_id = course_id
        await db.commit()
        return CourseMessageTeacherOut(
            thread_id=existing.id, created=False, course_context_label=label
        )

    db.add(
        ConversationParticipant(
            thread_id=thread.id,
            user_id=teacher.id,
            role=ConversationParticipantRole.teacher,
        )
    )
    db.add(
        ConversationParticipant(
            thread_id=thread.id,
            user_id=student.id,
            role=ConversationParticipantRole.student,
        )
    )
    for pid in parent_ids:
        db.add(
            ConversationParticipant(
                thread_id=thread.id,
                user_id=pid,
                role=ConversationParticipantRole.parent,
            )
        )

    names = await _user_names(db, [teacher.id, student.id, *parent_ids])
    thread.title = _default_title(
        thread_type=thread_type,
        student_name=names.get(student.id, student.name),
        teacher_name=names.get(teacher.id, teacher.name),
        parent_name=names.get(parent_ids[0], "") if parent_ids else "",
        participant_names=[names.get(pid, "") for pid in parent_ids],
    )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await _resolve_course_teacher_thread(
            db,
            course_id=course_id,
            student_id=student.id,
            teacher_id=teacher.id,
            parent_ids=parent_ids,
        )
        if not existing:
            raise
        await db.commit()
        return CourseMessageTeacherOut(
            thread_id=existing.id, created=False, course_context_label=label
        )

    await db.refresh(thread)
    return CourseMessageTeacherOut(
        thread_id=thread.id, created=True, course_context_label=label
    )
