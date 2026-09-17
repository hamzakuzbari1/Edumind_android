"""Parent ↔ teacher messaging: catalog of child's teachers and thread open/create."""



from __future__ import annotations



from fastapi import HTTPException, status

from sqlalchemy import select

from sqlalchemy.exc import IntegrityError

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import selectinload



from app.models.catalog import Course, TeacherProfile

from app.models.conversation import (

    ConversationParticipant,

    ConversationParticipantRole,

    ConversationThread,

    ConversationThreadType,

)

from app.models.user import User, UserRole

from app.schemas.parent_messaging import (

    ParentMessagingRecentOut,

    ParentMessagingSummaryOut,

    ParentTeacherChatOpenOut,

    ParentTeacherContactOut,

    ParentTeachersListOut,

)

from app.services.parent_link_service import list_linked_students, resolve_parent_student_id

from app.services.parent_teacher_thread_service import (

    find_parent_teacher_thread,

    thread_state_for_parent,

)

from app.services.student_courses_service import _access_map, _courses_for_grade, get_student_profile

from app.services.subscription_access_service import assert_student_active_enrollment, is_access_active

from app.utils.media_urls import teacher_avatar_url





def _display_str(value: str | None, fallback: str) -> str:

    text = (value or "").strip()

    return text or fallback





def _parent_teacher_title(parent_name: str, teacher_name: str) -> str:

    return f"{parent_name} ↔ {teacher_name}"





async def _load_course_for_parent_child(

    db: AsyncSession, parent: User, student_id: int, course_id: int

) -> tuple[Course, User, User]:

    await resolve_parent_student_id(db, parent, student_id)

    profile = await get_student_profile(db, student_id)

    result = await db.execute(

        select(Course)

        .where(Course.id == course_id, Course.is_active.is_(True))

        .options(

            selectinload(Course.subject),

            selectinload(Course.teacher_profile).selectinload(TeacherProfile.user),

        )

    )

    course = result.scalar_one_or_none()

    if not course or not course.is_published or not course.teacher_profile.active:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الدورة غير متاحة")

    if profile.grade and course.grade != profile.grade:

        raise HTTPException(

            status_code=status.HTTP_403_FORBIDDEN,

            detail="هذا المعلّم لا يدرّس صف ابنك",

        )

    student = await db.get(User, student_id)

    teacher = await db.get(User, course.teacher_profile.user_id)

    if not student or not teacher or teacher.role != UserRole.teacher:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المعلّم غير موجود")

    return course, student, teacher





async def _find_teacher_parent_thread(

    db: AsyncSession,

    *,

    parent_id: int,

    teacher_id: int,

    course_id: int,

) -> ConversationThread | None:

    result = await db.execute(

        select(ConversationThread).where(

            ConversationThread.thread_type == ConversationThreadType.teacher_parent,

            ConversationThread.parent_user_id == parent_id,

            ConversationThread.teacher_user_id == teacher_id,

            ConversationThread.course_id == course_id,

        )

    )

    threads = list(result.scalars().all())

    if not threads:

        return None

    if len(threads) == 1:

        return threads[0]

    return max(threads, key=lambda t: t.last_message_at or t.created_at)





async def list_parent_teacher_contacts(

    db: AsyncSession, parent: User

) -> ParentTeachersListOut:

    if parent.role != UserRole.parent:

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="لأولياء الأمور فقط")



    students = await list_linked_students(db, parent.id)

    contacts: list[ParentTeacherContactOut] = []

    seen: set[tuple[int, int, int]] = set()



    for student in students:

        profile = await get_student_profile(db, student.id)

        if not profile.grade:

            continue

        courses = await _courses_for_grade(db, profile.grade)

        access = await _access_map(db, student.id, [c.id for c in courses])

        for course in courses:

            if not is_access_active(access.get(course.id)):

                continue

            tp = course.teacher_profile

            key = (tp.user_id, student.id, course.id)

            if key in seen:

                continue

            seen.add(key)



            thread = await find_parent_teacher_thread(

                db,

                parent_id=parent.id,

                teacher_id=tp.user_id,

                student_id=student.id,

                course_id=course.id,

            )

            tid, preview, last_at, unread = await thread_state_for_parent(db, parent.id, thread)



            contacts.append(

                ParentTeacherContactOut(

                    teacher_user_id=tp.user_id,

                    teacher_profile_id=tp.id,

                    teacher_name=_display_str(tp.full_name, "معلّم"),

                    teacher_image_url=teacher_avatar_url(tp.image_url),

                    subject_name=_display_str(course.subject.name_ar, "مادة"),

                    course_id=course.id,

                    course_title=_display_str(course.title, "دورة"),

                    student_id=student.id,

                    student_name=_display_str(student.name, "طالب"),

                    thread_id=tid,

                    last_message_preview=preview,

                    last_message_at=last_at,

                    unread_count=unread,

                )

            )



    contacts.sort(

        key=lambda c: (

            c.unread_count > 0,

            c.last_message_at or "",

            c.teacher_name or "",

        ),

        reverse=True,

    )

    total_unread = sum(c.unread_count for c in contacts)

    return ParentTeachersListOut(teachers=contacts, total_unread=total_unread)





async def parent_messaging_summary(

    db: AsyncSession, parent: User

) -> ParentMessagingSummaryOut:

    data = await list_parent_teacher_contacts(db, parent)

    recent = [

        ParentMessagingRecentOut(

            thread_id=c.thread_id,

            teacher_name=c.teacher_name,

            teacher_image_url=c.teacher_image_url,

            student_name=c.student_name,

            subject_name=c.subject_name,

            last_message_preview=c.last_message_preview,

            last_message_at=c.last_message_at,

            unread_count=c.unread_count,

        )

        for c in data.teachers

        if c.thread_id and (c.last_message_preview or c.unread_count > 0)

    ]

    recent.sort(key=lambda r: (r.unread_count > 0, r.last_message_at or ""), reverse=True)

    return ParentMessagingSummaryOut(

        total_teachers=len(data.teachers),

        total_unread=data.total_unread,

        recent=recent[:8],

    )





async def open_parent_teacher_chat(

    db: AsyncSession,

    parent: User,

    teacher_id: int,

    *,

    student_id: int,

    course_id: int,

) -> ParentTeacherChatOpenOut:

    if parent.role != UserRole.parent:

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="لأولياء الأمور فقط")



    course, student, teacher = await _load_course_for_parent_child(

        db, parent, student_id, course_id

    )

    if teacher.id != teacher_id:

        raise HTTPException(

            status_code=status.HTTP_403_FORBIDDEN,

            detail="لا يمكنك مراسلة هذا المعلّم — غير مرتبط بابنك",

        )



    await assert_student_active_enrollment(db, student.id, course.id)



    parent_id = parent.id

    student_user_id = student.id

    teacher_user_id = teacher.id

    resolved_course_id = course.id

    parent_name = _display_str(parent.name, "ولي أمر")

    student_name = _display_str(student.name, "طالب")

    teacher_name = _display_str(course.teacher_profile.full_name, "معلّم")

    subject_name = _display_str(course.subject.name_ar, "مادة")

    context_label = f"{subject_name} — {student_name}"

    thread_title = _parent_teacher_title(parent_name, teacher_name)



    existing = await _find_teacher_parent_thread(

        db,

        parent_id=parent_id,

        teacher_id=teacher_user_id,

        course_id=resolved_course_id,

    )

    if existing:

        await db.commit()

        return ParentTeacherChatOpenOut(

            thread_id=existing.id,

            created=False,

            teacher_name=teacher_name,

            subject_name=subject_name,

            student_name=student_name,

            context_label=context_label,

        )



    thread = ConversationThread(

        thread_type=ConversationThreadType.teacher_parent,

        student_id=student_user_id,

        teacher_user_id=teacher_user_id,

        parent_user_id=parent_id,

        course_id=resolved_course_id,

        include_parent=False,

        created_by_user_id=parent_id,

        title=thread_title,

    )

    db.add(thread)

    try:

        await db.flush()

    except IntegrityError:

        await db.rollback()

        existing = await _find_teacher_parent_thread(

            db,

            parent_id=parent_id,

            teacher_id=teacher_user_id,

            course_id=resolved_course_id,

        )

        if not existing:

            raise

        await db.commit()

        return ParentTeacherChatOpenOut(

            thread_id=existing.id,

            created=False,

            teacher_name=teacher_name,

            subject_name=subject_name,

            student_name=student_name,

            context_label=context_label,

        )



    db.add(

        ConversationParticipant(

            thread_id=thread.id,

            user_id=teacher_user_id,

            role=ConversationParticipantRole.teacher,

        )

    )

    db.add(

        ConversationParticipant(

            thread_id=thread.id,

            user_id=parent_id,

            role=ConversationParticipantRole.parent,

        )

    )



    await db.commit()

    await db.refresh(thread)

    return ParentTeacherChatOpenOut(

        thread_id=thread.id,

        created=True,

        teacher_name=teacher_name,

        subject_name=subject_name,

        student_name=student_name,

        context_label=context_label,

    )
