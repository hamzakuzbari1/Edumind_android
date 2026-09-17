"""Seed and verify the minimal A3 DEV learning fixture.

This script is intentionally DEV-only data setup. It does not alter schema,
does not run migrations, and does not print credentials.
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import models as _models  # noqa: F401 - register SQLAlchemy relationships
from app.core.security import create_access_token, hash_password
from app.core.test_users import TEST_USER_PASSWORD, default_test_email, verified_at_for
from app.core.test_users import TEST_USERS_BY_KEY
from app.db.session import AsyncSessionLocal, engine
from app.models.catalog import Course, CourseUnit, Subject, TeacherProfile
from app.models.enrollment import (
    CourseEnrollment,
    CourseEnrollmentStatus,
    OnboardingStep,
    PaymentStatus,
    StudentCourseAccess,
)
from app.models.lesson import Lesson, LessonContentType, LessonStatus
from app.models.profile import StudentProfile
from app.models.progress import StudentLessonProgress
from app.models.user import User, UserRole


A3_COURSE_TITLE = "A3 DEV Learning Fixture Course"
A2_REUSABLE_TITLE = "A2 DEV Onboarding Verification Course"
A3_SUBJECT_SLUG = "a3-dev-learning"
A3_TEACHER_EMAIL = "test.a3.teacher@eduspark-test.dev"
A3_STUDENT_EMAIL = default_test_email("auth_student")


@dataclass(frozen=True)
class SeedResult:
    course_id: int
    course_title: str
    reused_course: bool
    student_id: int
    teacher_profile_id: int
    unit_ids: list[int]
    lesson_ids: list[int]
    enrollment_id: int
    access_id: int


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get_or_create_user(
    db,
    *,
    email: str,
    name: str,
    role: UserRole,
) -> User:
    normalized = email.strip().lower()
    user = await db.scalar(select(User).where(User.email == normalized))
    if user is None:
        user = User(
            email=normalized,
            name=name,
            role=role,
            hashed_password=hash_password(TEST_USER_PASSWORD),
            email_verified_at=_now(),
        )
        db.add(user)
        await db.flush()
    else:
        user.name = name
        user.role = role
        user.hashed_password = hash_password(TEST_USER_PASSWORD)
        user.email_verified_at = user.email_verified_at or _now()
    return user


async def _get_or_create_student(db) -> User:
    spec = TEST_USERS_BY_KEY["auth_student"]
    student = await _get_or_create_user(
        db,
        email=A3_STUDENT_EMAIL,
        name=spec.name,
        role=UserRole.student,
    )
    student.email_verified_at = verified_at_for(spec)
    profile = await db.scalar(select(StudentProfile).where(StudentProfile.user_id == student.id))
    if profile is None:
        profile = StudentProfile(
            user_id=student.id,
            interests_json="[]",
            hobbies_json="[]",
            grade=12,
            onboarding_step=OnboardingStep.complete,
            onboarding_completed_at=_now(),
            payment_completed_at=_now(),
        )
        db.add(profile)
    else:
        profile.grade = 12
        profile.onboarding_step = OnboardingStep.complete
        profile.onboarding_completed_at = profile.onboarding_completed_at or _now()
        profile.payment_completed_at = profile.payment_completed_at or _now()
    await db.flush()
    return student


async def _get_or_create_teacher_profile(db) -> TeacherProfile:
    teacher = await _get_or_create_user(
        db,
        email=A3_TEACHER_EMAIL,
        name="A3 DEV Teacher",
        role=UserRole.teacher,
    )
    profile = await db.scalar(select(TeacherProfile).where(TeacherProfile.user_id == teacher.id))
    if profile is None:
        profile = TeacherProfile(
            user_id=teacher.id,
            full_name="A3 DEV Teacher",
            bio="DEV fixture teacher for Android A3 learning flow.",
            rating=0.0,
            student_count=0,
            active=True,
            setup_completed_at=_now(),
        )
        db.add(profile)
        await db.flush()
    else:
        profile.full_name = "A3 DEV Teacher"
        profile.active = True
        profile.setup_completed_at = profile.setup_completed_at or _now()
    return profile


async def _get_or_create_subject(db) -> Subject:
    subject = await db.scalar(select(Subject).where(Subject.grade == 12, Subject.slug == A3_SUBJECT_SLUG))
    if subject is None:
        subject = Subject(
            name_ar="مادة A3 التجريبية",
            slug=A3_SUBJECT_SLUG,
            grade=12,
            is_active=True,
        )
        db.add(subject)
        await db.flush()
    else:
        subject.is_active = True
    return subject


async def _select_safe_existing_course(db) -> Course | None:
    result = await db.execute(
        select(Course)
        .join(TeacherProfile, Course.teacher_profile_id == TeacherProfile.id)
        .where(
            Course.grade == 12,
            Course.is_active.is_(True),
            Course.is_published.is_(True),
            TeacherProfile.active.is_(True),
            Course.title.in_([A2_REUSABLE_TITLE, A3_COURSE_TITLE]),
        )
        .options(selectinload(Course.subject), selectinload(Course.teacher_profile))
        .order_by(Course.title == A2_REUSABLE_TITLE, Course.id)
    )
    courses = list(result.scalars().all())
    for course in courses:
        if "DEV" in (course.title or ""):
            return course
    return None


async def _get_or_create_course(db, teacher_profile: TeacherProfile, subject: Subject) -> tuple[Course, bool]:
    existing = await _select_safe_existing_course(db)
    if existing is not None:
        existing.is_active = True
        existing.is_published = True
        return existing, True

    course = await db.scalar(select(Course).where(Course.title == A3_COURSE_TITLE, Course.grade == 12))
    if course is None:
        course = Course(
            title=A3_COURSE_TITLE,
            description="Small DEV fixture for Android course/unit/lesson integration.",
            subject_id=subject.id,
            teacher_profile_id=teacher_profile.id,
            grade=12,
            price=0.0,
            currency="SYP",
            is_active=True,
            is_published=True,
        )
        db.add(course)
        await db.flush()
    else:
        course.subject_id = subject.id
        course.teacher_profile_id = teacher_profile.id
        course.is_active = True
        course.is_published = True
        course.price = 0.0
    return course, False


async def _cleanup_unused_a3_bootstrap_rows(db, *, reused_course: bool) -> None:
    if not reused_course:
        return

    subject = await db.scalar(select(Subject).where(Subject.slug == A3_SUBJECT_SLUG))
    if subject is not None:
        course_count = int(
            await db.scalar(
                select(func.count()).select_from(Course).where(Course.subject_id == subject.id)
            )
            or 0
        )
        if course_count == 0:
            await db.delete(subject)

    teacher = await db.scalar(select(User).where(User.email == A3_TEACHER_EMAIL))
    if teacher is not None:
        profile = await db.scalar(select(TeacherProfile).where(TeacherProfile.user_id == teacher.id))
        if profile is not None:
            course_count = int(
                await db.scalar(
                    select(func.count())
                    .select_from(Course)
                    .where(Course.teacher_profile_id == profile.id)
                )
                or 0
            )
            if course_count == 0:
                await db.delete(profile)
                await db.flush()
                await db.delete(teacher)


async def _get_or_create_unit(db, *, course_id: int, title: str, sort_order: int) -> CourseUnit:
    result = await db.execute(
        select(CourseUnit)
        .where(CourseUnit.course_id == course_id, CourseUnit.title == title)
        .order_by(CourseUnit.id)
        .limit(1)
    )
    unit = result.scalar_one_or_none()
    if unit is None:
        unit = CourseUnit(
            course_id=course_id,
            title=title,
            description=f"{title} - Android A3 DEV fixture",
            sort_order=sort_order,
            is_visible=True,
        )
        db.add(unit)
        await db.flush()
    else:
        unit.description = f"{title} - Android A3 DEV fixture"
        unit.sort_order = sort_order
        unit.is_visible = True
    return unit


async def _get_or_create_lesson(
    db,
    *,
    course: Course,
    unit: CourseUnit,
    teacher_user_id: int,
    title: str,
    sort_order: int,
) -> Lesson:
    result = await db.execute(
        select(Lesson)
        .where(Lesson.course_id == course.id, Lesson.title == title)
        .order_by(Lesson.id)
        .limit(1)
    )
    lesson = result.scalar_one_or_none()
    if lesson is None:
        lesson = Lesson(
            teacher_id=teacher_user_id,
            course_id=course.id,
            unit_id=unit.id,
            title=title,
            description=f"{title} DEV learning fixture.",
            preview=f"تجربة تعليمية قصيرة لدرس {title}.",
            subject=course.subject.name_ar if course.subject else "مادة A3 التجريبية",
            grade="12",
            sort_order=sort_order,
            is_visible=True,
            status=LessonStatus.processed,
            content_type=LessonContentType.video,
            video_url=f"/uploads/dev/a3/{course.id}/{unit.id}/{sort_order}.mp4",
        )
        db.add(lesson)
        await db.flush()
    else:
        lesson.teacher_id = teacher_user_id
        lesson.course_id = course.id
        lesson.unit_id = unit.id
        lesson.description = f"{title} DEV learning fixture."
        lesson.preview = f"تجربة تعليمية قصيرة لدرس {title}."
        lesson.subject = course.subject.name_ar if course.subject else "مادة A3 التجريبية"
        lesson.grade = "12"
        lesson.sort_order = sort_order
        lesson.is_visible = True
        lesson.status = LessonStatus.processed
        lesson.content_type = LessonContentType.video
        lesson.video_url = f"/uploads/dev/a3/{course.id}/{unit.id}/{sort_order}.mp4"
        lesson.pdf_path = None
        lesson.homework_path = None
    return lesson


async def _get_or_create_enrollment_access(
    db,
    *,
    student_id: int,
    course_id: int,
) -> tuple[CourseEnrollment, StudentCourseAccess]:
    enrollment = await db.scalar(
        select(CourseEnrollment)
        .where(
            CourseEnrollment.student_id == student_id,
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.status.in_(
                [
                    CourseEnrollmentStatus.pending.value,
                    CourseEnrollmentStatus.active.value,
                    CourseEnrollmentStatus.paused.value,
                ]
            ),
        )
        .order_by(CourseEnrollment.id)
        .limit(1)
    )
    if enrollment is None:
        enrollment = CourseEnrollment(
            student_id=student_id,
            course_id=course_id,
            status=CourseEnrollmentStatus.active.value,
            source="manual_grant",
            started_at=_now(),
        )
        db.add(enrollment)
        await db.flush()
    else:
        enrollment.status = CourseEnrollmentStatus.active.value
        enrollment.source = enrollment.source or "manual_grant"
        enrollment.started_at = enrollment.started_at or _now()

    access = await db.scalar(
        select(StudentCourseAccess).where(
            StudentCourseAccess.student_id == student_id,
            StudentCourseAccess.course_id == course_id,
        )
    )
    if access is None:
        access = StudentCourseAccess(
            student_id=student_id,
            course_id=course_id,
            payment_status=PaymentStatus.paid,
        )
        db.add(access)
        await db.flush()
    access.enrollment_id = enrollment.id
    access.payment_status = PaymentStatus.paid
    access.access_status = "active"
    access.source = "manual_grant"
    access.unlocked_at = access.unlocked_at or _now()
    access.activated_at = access.activated_at or _now()
    access.granted_at = access.granted_at or _now()
    access.revoked_at = None
    access.revocation_reason = None
    access.expires_at = _now() + timedelta(days=365)
    return enrollment, access


async def _reset_progress_fixture(db, *, student_id: int, lessons: list[Lesson]) -> None:
    for index, lesson in enumerate(lessons):
        row = await db.scalar(
            select(StudentLessonProgress).where(
                StudentLessonProgress.student_id == student_id,
                StudentLessonProgress.lesson_id == lesson.id,
            )
        )
        if row is None:
            row = StudentLessonProgress(student_id=student_id, lesson_id=lesson.id)
            db.add(row)
            await db.flush()
        row.quiz_submitted = False
        row.quiz_score_percent = 0.0
        row.pdf_opened = False
        row.pdf_progress_percent = 0.0
        row.completed_at = None
        row.completion_type = None
        if index == 0:
            row.started_at = _now()
            row.video_progress_percent = 35.0
            row.completion_percentage = 35.0
        else:
            row.started_at = None
            row.video_progress_percent = 0.0
            row.completion_percentage = 0.0
        row.updated_at = _now()


async def seed_fixture() -> SeedResult:
    async with AsyncSessionLocal() as db:
        student = await _get_or_create_student(db)
        course = await _select_safe_existing_course(db)
        if course is not None:
            reused = True
            await _cleanup_unused_a3_bootstrap_rows(db, reused_course=True)
        else:
            teacher_profile = await _get_or_create_teacher_profile(db)
            subject = await _get_or_create_subject(db)
            course, reused = await _get_or_create_course(db, teacher_profile, subject)

        if "subject" not in course.__dict__ or course.subject is None:
            await db.refresh(course, attribute_names=["subject"])
        if "teacher_profile" not in course.__dict__ or course.teacher_profile is None:
            await db.refresh(course, attribute_names=["teacher_profile"])

        unit_one = await _get_or_create_unit(
            db, course_id=course.id, title="A3 Unit 1 - Foundations", sort_order=1
        )
        unit_two = await _get_or_create_unit(
            db, course_id=course.id, title="A3 Unit 2 - Practice", sort_order=2
        )

        lessons = [
            await _get_or_create_lesson(
                db,
                course=course,
                unit=unit_one,
                teacher_user_id=course.teacher_profile.user_id,
                title="A3 Lesson 1.1 - Start Here",
                sort_order=1,
            ),
            await _get_or_create_lesson(
                db,
                course=course,
                unit=unit_one,
                teacher_user_id=course.teacher_profile.user_id,
                title="A3 Lesson 1.2 - Core Idea",
                sort_order=2,
            ),
            await _get_or_create_lesson(
                db,
                course=course,
                unit=unit_two,
                teacher_user_id=course.teacher_profile.user_id,
                title="A3 Lesson 2.1 - Guided Practice",
                sort_order=1,
            ),
            await _get_or_create_lesson(
                db,
                course=course,
                unit=unit_two,
                teacher_user_id=course.teacher_profile.user_id,
                title="A3 Lesson 2.2 - Wrap Up",
                sort_order=2,
            ),
        ]

        enrollment, access = await _get_or_create_enrollment_access(
            db, student_id=student.id, course_id=course.id
        )
        await _reset_progress_fixture(db, student_id=student.id, lessons=lessons)
        await db.commit()

        return SeedResult(
            course_id=course.id,
            course_title=course.title,
            reused_course=reused,
            student_id=student.id,
            teacher_profile_id=course.teacher_profile_id,
            unit_ids=[unit_one.id, unit_two.id],
            lesson_ids=[lesson.id for lesson in lessons],
            enrollment_id=enrollment.id,
            access_id=access.id,
        )


async def _count_fixture_rows(result: SeedResult) -> dict[str, int]:
    async with AsyncSessionLocal() as db:
        unit_count = int(
            await db.scalar(
                select(func.count()).select_from(CourseUnit).where(CourseUnit.id.in_(result.unit_ids))
            )
            or 0
        )
        lesson_count = int(
            await db.scalar(
                select(func.count()).select_from(Lesson).where(Lesson.id.in_(result.lesson_ids))
            )
            or 0
        )
        access_count = int(
            await db.scalar(
                select(func.count())
                .select_from(StudentCourseAccess)
                .where(
                    StudentCourseAccess.student_id == result.student_id,
                    StudentCourseAccess.course_id == result.course_id,
                )
            )
            or 0
        )
        return {
            "units": unit_count,
            "lessons": lesson_count,
            "access_rows": access_count,
        }


def _auth_headers(student_id: int) -> dict[str, str]:
    token = create_access_token({"sub": str(student_id), "role": "student"})
    return {"Authorization": f"Bearer {token}"}


async def verify_api_flow(result: SeedResult) -> dict[str, Any]:
    from app.main import app

    headers = _auth_headers(result.student_id)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://a3-dev-fixture",
        follow_redirects=False,
    ) as client:
        course = await client.get(f"/api/student/courses/{result.course_id}", headers=headers)
        units = await client.get(f"/api/student/courses/{result.course_id}/units", headers=headers)
        lesson = await client.get(f"/api/student/lessons/{result.lesson_ids[0]}", headers=headers)
        resume_before = await client.get(f"/api/student/courses/{result.course_id}/resume", headers=headers)
        start = await client.post(
            f"/api/student/lessons/{result.lesson_ids[0]}/progress",
            headers=headers,
            json={"video_percent": 40},
        )
        update = await client.post(
            f"/api/student/lessons/{result.lesson_ids[0]}/progress",
            headers=headers,
            json={"video_percent": 95},
        )
        complete = await client.post(
            f"/api/student/lessons/{result.lesson_ids[0]}/verify-completion",
            headers=headers,
        )
        resume_after = await client.get(f"/api/student/courses/{result.course_id}/resume", headers=headers)

    responses = {
        "course": course,
        "units": units,
        "lesson": lesson,
        "resume_before": resume_before,
        "start": start,
        "update": update,
        "complete": complete,
        "resume_after": resume_after,
    }
    status_codes = {name: response.status_code for name, response in responses.items()}
    failed = {name: response.text for name, response in responses.items() if response.status_code >= 400}
    if failed:
        return {"ok": False, "status_codes": status_codes, "errors": failed}

    course_json = course.json()
    units_json = units.json()
    lesson_json = lesson.json()
    resume_before_json = resume_before.json()
    start_json = start.json()
    update_json = update.json()
    complete_json = complete.json()
    resume_after_json = resume_after.json()

    ordering_ok = (
        [unit["id"] for unit in units_json] == result.unit_ids
        and [lesson["id"] for lesson in units_json[0]["lessons"]] == result.lesson_ids[:2]
        and [lesson["id"] for lesson in units_json[1]["lessons"]] == result.lesson_ids[2:]
    )
    checks = {
        "course_unlocked": course_json.get("unlocked") is True,
        "course_units_present": len(course_json.get("units") or []) == 2,
        "units_ordering": ordering_ok,
        "lesson_unit_id": lesson_json.get("unit_id") == result.unit_ids[0],
        "resume_before_first_lesson": (resume_before_json or {}).get("lesson_id") == result.lesson_ids[0],
        "start_progress": float(start_json.get("video_progress_percent") or 0) >= 40,
        "update_can_verify": update_json.get("can_verify") is True,
        "complete_success": complete_json.get("success") is True,
        "resume_after_moves_forward": (resume_after_json or {}).get("lesson_id") == result.lesson_ids[1],
    }
    return {
        "ok": all(checks.values()),
        "status_codes": status_codes,
        "checks": checks,
        "resume_before": resume_before_json,
        "resume_after": resume_after_json,
    }


async def main_async() -> dict[str, Any]:
    first = await seed_fixture()
    first_counts = await _count_fixture_rows(first)
    second = await seed_fixture()
    second_counts = await _count_fixture_rows(second)
    idempotent = first == second and first_counts == second_counts
    api = await verify_api_flow(second)
    final_seed = await seed_fixture()

    report = {
        "seed": asdict(final_seed),
        "idempotency": {
            "ok": idempotent,
            "first": asdict(first),
            "second": asdict(second),
            "counts": second_counts,
        },
        "final_state": {
            "restored_for_android": final_seed == second,
            "resume_lesson_id": final_seed.lesson_ids[0],
            "resume_seed_percent": 35,
        },
        "api": api,
    }
    await engine.dispose()
    return report


def main() -> int:
    report = asyncio.run(main_async())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["idempotency"]["ok"] and report["api"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
