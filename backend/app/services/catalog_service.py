"""Catalog queries: grades, subjects, teachers."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.demo_guard import is_demo_email, is_demo_teacher_name
from app.db.sql_types import user_role_equals
from app.models.catalog import Course, Subject, TeacherProfile, TeacherProfileGrade, TeacherProfileSubject
from app.models.user import User, UserRole
from app.schemas.catalog import CoursePreviewOut, GradeOut, SubjectOut, TeacherCardOut
from app.core.academic_grades import ACADEMIC_GRADES, GRADE_LABELS
from app.core.reference_catalog import ensure_reference_subjects, is_subject_allowed_for_grade
from app.utils.media_urls import public_upload_url, teacher_avatar_url

def course_summary(course: Course) -> str:
    bio = (course.teacher_profile.bio or "").strip()
    if bio:
        return bio if len(bio) <= 140 else f"{bio[:137]}..."
    return (
        f"دروس تفاعلية ومتابعة ذكية في {course.subject.name_ar} "
        f"مع {course.teacher_profile.full_name}."
    )


def list_grades() -> list[GradeOut]:
    return [GradeOut(value=g, label_ar=GRADE_LABELS[g]) for g in ACADEMIC_GRADES]


async def list_subjects_for_grade(db: AsyncSession, grade: int) -> list[SubjectOut]:
    await ensure_reference_subjects(db, grades=range(grade, grade + 1))
    result = await db.execute(
        select(Subject)
        .where(Subject.grade == grade, Subject.is_active.is_(True))
        .order_by(Subject.name_ar)
    )
    return [
        SubjectOut(id=s.id, name_ar=s.name_ar, slug=s.slug, grade=s.grade)
        for s in result.scalars().all()
        if is_subject_allowed_for_grade(s.slug, s.grade)
    ]


async def list_teachers_for_subject(
    db: AsyncSession, *, subject_id: int, grade: int
) -> list[TeacherCardOut]:
    subj = await db.get(Subject, subject_id)
    if not subj or subj.grade != grade:
        return []

    # Teacher discovery is profile-based: completed + active teacher who saved this
    # subject and grade. A Course row is not required and must not be auto-created.
    result = await db.execute(
        select(TeacherProfile)
        .join(User, TeacherProfile.user_id == User.id)
        .join(TeacherProfileSubject, TeacherProfileSubject.teacher_profile_id == TeacherProfile.id)
        .join(TeacherProfileGrade, TeacherProfileGrade.teacher_profile_id == TeacherProfile.id)
        .where(
            TeacherProfile.active.is_(True),
            TeacherProfile.setup_completed_at.is_not(None),
            user_role_equals(UserRole.teacher),
            TeacherProfileSubject.subject_id == subject_id,
            TeacherProfileGrade.grade == grade,
        )
        .options(selectinload(TeacherProfile.user))
    )
    teachers = result.scalars().unique().all()
    cards = []
    for t in teachers:
        if is_demo_email(t.user.email if t.user else None) or is_demo_teacher_name(t.full_name):
            continue
        cards.append(
            TeacherCardOut(
                id=t.id,
                full_name=t.full_name,
                image_url=teacher_avatar_url(t.image_url),
                bio=t.bio,
                rating=round(t.rating, 1),
                student_count=t.student_count,
                subject_id=subject_id,
                subject_name=subj.name_ar,
            )
        )
    return cards


async def teacher_is_selectable_for_subject(
    db: AsyncSession, *, teacher_profile_id: int, subject_id: int, grade: int
) -> bool:
    teachers = await list_teachers_for_subject(db, subject_id=subject_id, grade=grade)
    return any(card.id == teacher_profile_id for card in teachers)


async def get_course_for_teacher_subject(
    db: AsyncSession, *, subject_id: int, teacher_profile_id: int, grade: int
) -> Course | None:
    result = await db.execute(
        select(Course)
        .join(TeacherProfile, Course.teacher_profile_id == TeacherProfile.id)
        .where(
            Course.subject_id == subject_id,
            Course.teacher_profile_id == teacher_profile_id,
            Course.grade == grade,
            Course.is_active.is_(True),
            Course.is_published.is_(True),
            TeacherProfile.active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def course_to_preview(db: AsyncSession, course: Course) -> CoursePreviewOut:
    await db.refresh(course, ["subject", "teacher_profile"])
    return CoursePreviewOut(
        id=course.id,
        title=course.title,
        subject_name=course.subject.name_ar,
        teacher_name=course.teacher_profile.full_name,
        teacher_image_url=teacher_avatar_url(course.teacher_profile.image_url),
        summary=course_summary(course),
        grade=course.grade,
        price=course.price,
        currency=course.currency,
    )


async def list_courses_by_ids(db: AsyncSession, course_ids: list[int]) -> list[CoursePreviewOut]:
    if not course_ids:
        return []
    result = await db.execute(
        select(Course)
        .where(Course.id.in_(course_ids))
        .options(
            selectinload(Course.subject),
            selectinload(Course.teacher_profile),
        )
    )
    out = []
    for c in result.scalars().all():
        out.append(
            CoursePreviewOut(
                id=c.id,
                title=c.title,
                subject_name=c.subject.name_ar,
                teacher_name=c.teacher_profile.full_name,
                teacher_image_url=teacher_avatar_url(c.teacher_profile.image_url),
                summary=course_summary(c),
                grade=c.grade,
                price=c.price,
                currency=c.currency,
            )
        )
    return out
