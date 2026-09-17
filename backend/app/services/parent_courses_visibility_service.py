"""Parent view of student enrolled / available subjects and teachers."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.parent_courses_visibility import ParentSubjectCourseOut, ParentSubjectsTeachersOut
from app.services.parent_link_service import resolve_parent_student_id
from app.services.parent_teacher_thread_service import (
    find_parent_teacher_thread,
    thread_state_for_parent,
)
from app.services.parent_student_context_service import grade_label
from app.services.student_courses_service import (
    _access_map,
    _build_course_card,
    _courses_for_grade,
    get_student_profile,
)
from app.utils.media_urls import teacher_avatar_url


async def _course_to_parent_item(
    db: AsyncSession,
    *,
    parent_id: int,
    student_id: int,
    course,
    access: dict,
) -> ParentSubjectCourseOut:
    card = await _build_course_card(db, student_id, course, access)
    tp = course.teacher_profile
    thread = await find_parent_teacher_thread(
        db,
        parent_id=parent_id,
        teacher_id=tp.user_id,
        student_id=student_id,
        course_id=course.id,
    )
    tid, _, _, unread = await thread_state_for_parent(db, parent_id, thread)

    avatar = teacher_avatar_url(tp.image_url)
    return ParentSubjectCourseOut(
        subject_id=course.subject_id,
        subject_name=course.subject.name_ar,
        course_id=course.id,
        course_title=course.title,
        teacher_user_id=tp.user_id,
        teacher_profile_id=tp.id,
        teacher_name=tp.full_name,
        teacher_image_url=avatar,
        enrolled=card.unlocked,
        subscription_status=card.subscription_status,
        progress_percent=card.progress_percent,
        lesson_count=card.lesson_count,
        completed_lesson_count=card.completed_lesson_count,
        thread_id=tid,
        unread_count=unread,
    )


async def build_parent_subjects_teachers(
    db: AsyncSession,
    parent: User,
    student_id: int,
) -> ParentSubjectsTeachersOut:
    sid = await resolve_parent_student_id(db, parent, student_id)
    student = await db.get(User, sid)
    profile = await get_student_profile(db, sid)

    if not profile.grade:
        return ParentSubjectsTeachersOut(
            student_id=sid,
            student_name=student.name if student else "",
            grade=None,
            grade_label="",
            has_grade=False,
        )

    courses = await _courses_for_grade(db, profile.grade)
    access = await _access_map(db, sid, [c.id for c in courses])

    enrolled: list[ParentSubjectCourseOut] = []
    available: list[ParentSubjectCourseOut] = []

    for course in courses:
        item = await _course_to_parent_item(
            db,
            parent_id=parent.id,
            student_id=sid,
            course=course,
            access=access,
        )
        if item.enrolled:
            enrolled.append(item)
        else:
            available.append(item)

    return ParentSubjectsTeachersOut(
        student_id=sid,
        student_name=student.name if student else "",
        grade=profile.grade,
        grade_label=grade_label(profile.grade),
        enrolled=enrolled,
        available=available,
        enrolled_count=len(enrolled),
        available_count=len(available),
        has_grade=True,
    )
