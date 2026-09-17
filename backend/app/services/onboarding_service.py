"""Student onboarding persistence."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.academic_grades import validate_academic_grade

from app.models.catalog import Subject
from app.models.enrollment import (
    OnboardingStep,
    PaymentStatus,
    StudentCourseAccess,
    StudentSubjectChoice,
    StudentTeacherChoice,
)
from app.schemas.catalog import CoursePreviewOut
from app.schemas.onboarding import OnboardingStatusOut, TeacherChoiceItem
from app.services.catalog_service import (
    course_to_preview,
    get_course_for_teacher_subject,
    teacher_is_selectable_for_subject,
)
from app.services.user_status_service import get_student_profile


async def get_onboarding_status(db: AsyncSession, student_id: int) -> OnboardingStatusOut:
    profile = await get_student_profile(db, student_id)

    subj_result = await db.execute(
        select(StudentSubjectChoice.subject_id).where(StudentSubjectChoice.student_id == student_id)
    )
    subject_ids = list(subj_result.scalars().all())

    teach_result = await db.execute(
        select(StudentTeacherChoice).where(StudentTeacherChoice.student_id == student_id)
    )
    teacher_choices = [
        {"subject_id": c.subject_id, "teacher_profile_id": c.teacher_profile_id}
        for c in teach_result.scalars().all()
    ]

    onboarding_complete = profile.onboarding_completed_at is not None
    payment_complete = profile.payment_completed_at is not None

    step = (
        profile.onboarding_step.value
        if profile.onboarding_step
        else OnboardingStep.grade.value
    )

    return OnboardingStatusOut(
        step=step,
        grade=profile.grade,
        onboarding_complete=onboarding_complete,
        needs_payment=False,
        payment_complete=payment_complete,
        selected_subject_ids=subject_ids,
        teacher_choices=teacher_choices,
    )


async def save_grade(db: AsyncSession, student_id: int, grade: int) -> OnboardingStatusOut:
    validate_academic_grade(grade)
    profile = await get_student_profile(db, student_id)
    profile.grade = grade
    profile.onboarding_step = OnboardingStep.subjects
    profile.onboarding_completed_at = None
    profile.payment_completed_at = None

    await db.execute(delete(StudentSubjectChoice).where(StudentSubjectChoice.student_id == student_id))
    await db.execute(delete(StudentTeacherChoice).where(StudentTeacherChoice.student_id == student_id))
    await db.execute(
        delete(StudentCourseAccess).where(
            StudentCourseAccess.student_id == student_id,
            StudentCourseAccess.payment_status != PaymentStatus.paid,
        )
    )
    await db.flush()
    return await get_onboarding_status(db, student_id)


async def save_subjects(db: AsyncSession, student_id: int, subject_ids: list[int]) -> OnboardingStatusOut:
    profile = await get_student_profile(db, student_id)
    if not profile.grade:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اختر الصف أولاً")

    result = await db.execute(
        select(Subject).where(
            Subject.id.in_(subject_ids),
            Subject.grade == profile.grade,
            Subject.is_active.is_(True),
        )
    )
    found = {s.id for s in result.scalars().all()}
    if len(found) != len(set(subject_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="مواد غير صالحة لهذا الصف")

    await db.execute(delete(StudentSubjectChoice).where(StudentSubjectChoice.student_id == student_id))
    await db.execute(delete(StudentTeacherChoice).where(StudentTeacherChoice.student_id == student_id))

    for sid in subject_ids:
        db.add(StudentSubjectChoice(student_id=student_id, subject_id=sid))

    profile.onboarding_step = OnboardingStep.teachers
    await db.flush()
    return await get_onboarding_status(db, student_id)


async def save_teachers(
    db: AsyncSession, student_id: int, choices: list[TeacherChoiceItem]
) -> OnboardingStatusOut:
    profile = await get_student_profile(db, student_id)
    if not profile.grade:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="أكمل الخطوات السابقة")

    subj_result = await db.execute(
        select(StudentSubjectChoice.subject_id).where(StudentSubjectChoice.student_id == student_id)
    )
    allowed_subjects = set(subj_result.scalars().all())
    chosen_subjects = {c.subject_id for c in choices}
    if chosen_subjects != allowed_subjects:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="يجب اختيار معلم لكل مادة محددة",
        )

    await db.execute(delete(StudentTeacherChoice).where(StudentTeacherChoice.student_id == student_id))
    for c in choices:
        selectable = await teacher_is_selectable_for_subject(
            db,
            teacher_profile_id=c.teacher_profile_id,
            subject_id=c.subject_id,
            grade=profile.grade,
        )
        if not selectable:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="المعلم المختار غير متاح لهذه المادة",
            )
        db.add(
            StudentTeacherChoice(
                student_id=student_id,
                subject_id=c.subject_id,
                teacher_profile_id=c.teacher_profile_id,
            )
        )

    await db.flush()
    return await get_onboarding_status(db, student_id)


async def complete_onboarding(db: AsyncSession, student_id: int) -> tuple[list[CoursePreviewOut], OnboardingStatusOut]:
    profile = await get_student_profile(db, student_id)
    if not profile.grade:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="أكمل اختيار الصف")

    teach_result = await db.execute(
        select(StudentTeacherChoice).where(StudentTeacherChoice.student_id == student_id)
    )
    choices = teach_result.scalars().all()
    if not choices:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اختر المعلمين أولاً")

    previews: list[CoursePreviewOut] = []
    for choice in choices:
        course = await get_course_for_teacher_subject(
            db,
            subject_id=choice.subject_id,
            teacher_profile_id=choice.teacher_profile_id,
            grade=profile.grade,
        )
        if not course:
            continue

        existing = await db.execute(
            select(StudentCourseAccess).where(
                StudentCourseAccess.student_id == student_id,
                StudentCourseAccess.course_id == course.id,
            )
        )
        access = existing.scalar_one_or_none()
        if not access:
            access = StudentCourseAccess(
                student_id=student_id,
                course_id=course.id,
                payment_status=PaymentStatus.pending,
            )
            db.add(access)
        elif access.payment_status != PaymentStatus.paid:
            access.payment_status = PaymentStatus.pending

        previews.append(await course_to_preview(db, course))

    profile.onboarding_step = OnboardingStep.complete
    profile.onboarding_completed_at = datetime.now(timezone.utc)
    await db.flush()
    status_out = await get_onboarding_status(db, student_id)
    return previews, status_out
