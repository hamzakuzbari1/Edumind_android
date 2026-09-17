"""Student dashboard & subscriptions — all grade courses from real teachers."""

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.demo_guard import is_demo_email, is_demo_teacher_name
from app.db.sql_types import user_role_equals
from app.models.catalog import Course, CourseUnit, TeacherProfile
from app.models.parent_link import ParentStudentLink
from app.models.user import User, UserRole
from app.models.enrollment import CourseAccessStatus, PaymentStatus, StudentCourseAccess
from app.services.subscription_access_service import (
    days_until_expiry,
    is_access_active,
    subscription_lifecycle_status,
    _aware,
)
from app.models.lesson import Lesson, LessonAsset, LessonContentType, LessonStatus
from app.models.progress import StudentLessonProgress
from app.schemas.student_courses import (
    CourseLessonOut,
    StudentCourseCardOut,
    StudentCourseDetailOut,
    StudentCourseResumeLessonOut,
    StudentCourseTeacherProfileOut,
    StudentCourseUnitOut,
    StudentDashboardOut,
    StudentLessonStatusOut,
)
from app.schemas.subscriptions import SubscriptionCourseOut, SubscriptionsCatalogOut
from app.services.user_status_service import get_student_profile
from app.utils.media_urls import public_upload_url, teacher_avatar_url

settings = get_settings()
logger = logging.getLogger(__name__)

from app.services.lesson_assets_service import assets_public_urls, sync_lesson_legacy_columns
from app.services.lesson_capabilities import (
    build_lesson_capabilities,
    lesson_is_visible,
    resolve_lesson_content_type,
)

LESSON_TYPE_LABELS = {
    "video": "فيديو",
    "pdf": "PDF",
    "homework": "واجب",
    "ai": "ذكي",
    "composite": "درس متكامل",
}


def _public_url(path: str | None) -> str | None:
    return public_upload_url(path)


def _is_real_catalog_teacher(course: Course) -> bool:
    tp = course.teacher_profile
    user = getattr(tp, "user", None)
    role = getattr(user.role, "value", user.role) if user else None
    if user and role != "teacher":
        return False
    if is_demo_email(user.email if user else None) or is_demo_teacher_name(tp.full_name):
        return False
    return True


async def _completed_lesson_ids(db: AsyncSession, student_id: int, lesson_ids: list[int]) -> set[int]:
    if not lesson_ids:
        return set()
    result = await db.execute(
        select(StudentLessonProgress.lesson_id).where(
            StudentLessonProgress.student_id == student_id,
            StudentLessonProgress.lesson_id.in_(lesson_ids),
            StudentLessonProgress.completed_at.is_not(None),
        )
    )
    return set(result.scalars().all())


async def _progress_map(
    db: AsyncSession, student_id: int, lesson_ids: list[int]
) -> dict[int, StudentLessonProgress]:
    if not lesson_ids:
        return {}
    result = await db.execute(
        select(StudentLessonProgress).where(
            StudentLessonProgress.student_id == student_id,
            StudentLessonProgress.lesson_id.in_(lesson_ids),
        )
    )
    return {row.lesson_id: row for row in result.scalars().all()}


async def _course_lessons(db: AsyncSession, course_id: int) -> list[Lesson]:
    result = await db.execute(
        select(Lesson)
        .where(Lesson.course_id == course_id)
        .options(selectinload(Lesson.assets).selectinload(LessonAsset.media_object))
        .order_by(Lesson.sort_order, Lesson.id)
    )
    visible: list[Lesson] = []
    for lesson in result.scalars().all():
        sync_lesson_legacy_columns(lesson)
        if lesson_is_visible(lesson):
            visible.append(lesson)
    return visible


async def _course_units(db: AsyncSession, course_id: int) -> list[CourseUnit]:
    result = await db.execute(
        select(CourseUnit)
        .where(CourseUnit.course_id == course_id, CourseUnit.is_visible.is_(True))
        .order_by(CourseUnit.sort_order, CourseUnit.id)
    )
    return list(result.scalars().all())


async def _access_map(db: AsyncSession, student_id: int, course_ids: list[int]) -> dict[int, StudentCourseAccess]:
    if not course_ids:
        return {}
    result = await db.execute(
        select(StudentCourseAccess).where(
            StudentCourseAccess.student_id == student_id,
            StudentCourseAccess.course_id.in_(course_ids),
        ).options(selectinload(StudentCourseAccess.enrollment))
    )
    return {a.course_id: a for a in result.scalars().all()}


def _lock_reason(access: StudentCourseAccess | None) -> str | None:
    if access is None:
        return "اشترك لفتح المادة"
    access_status = access.access_status or ""
    if access_status == CourseAccessStatus.revoked.value:
        return "تم إلغاء الوصول لهذه المادة"
    if access_status == CourseAccessStatus.suspended.value:
        return "الوصول لهذه المادة موقوف مؤقتاً"
    if access_status == CourseAccessStatus.pending.value or access.payment_status == PaymentStatus.pending:
        return "اشترك لفتح المادة"
    if not is_access_active(access):
        return "انتهى الاشتراك — جدّد للوصول"
    return None


async def _courses_for_grade(db: AsyncSession, grade: int) -> list[Course]:
    """All published courses for a grade from active teachers (real DB catalog)."""
    result = await db.execute(
        select(Course)
        .join(TeacherProfile, Course.teacher_profile_id == TeacherProfile.id)
        .join(User, TeacherProfile.user_id == User.id)
        .where(
            Course.grade == grade,
            Course.is_active.is_(True),
            Course.is_published.is_(True),
            TeacherProfile.active.is_(True),
            user_role_equals(UserRole.teacher),
        )
        .options(
            selectinload(Course.subject),
            selectinload(Course.teacher_profile).selectinload(TeacherProfile.user),
        )
        .order_by(Course.subject_id, Course.teacher_profile_id)
    )
    courses = [c for c in result.scalars().all() if _is_real_catalog_teacher(c)]
    logger.debug("courses_for_grade grade=%s count=%s", grade, len(courses))
    return courses


def _lesson_counts(lessons: list[Lesson]) -> dict[str, int]:
    counts = {"video": 0, "pdf": 0, "homework": 0, "ai": 0, "composite": 0}
    for lesson in lessons:
        ctype = resolve_lesson_content_type(lesson)
        if ctype in counts:
            counts[ctype] += 1
        elif ctype == "composite":
            counts["composite"] += 1
            if lesson.video_url:
                counts["video"] += 1
            if lesson.pdf_path:
                counts["pdf"] += 1
    return counts


def _subscription_benefits(lessons: list[Lesson], subject_name: str) -> str:
    total = len(lessons)
    if total == 0:
        return f"اشتراك في {subject_name} — سيُضاف المحتوى فور رفعه من المعلم."
    counts = _lesson_counts(lessons)
    parts = [f"يشمل {total} دروس في {subject_name}"]
    if counts["video"]:
        parts.append(f"{counts['video']} فيديو")
    if counts["pdf"]:
        parts.append(f"{counts['pdf']} ملف PDF")
    if counts["homework"]:
        parts.append(f"{counts['homework']} واجب")
    if counts["ai"]:
        parts.append("دروس ذكية مع معلم AI")
    parts.append("متابعة ذكية ومخطط دراسي")
    return "، ".join(parts) + "."


def _progress_payload(row: StudentLessonProgress | None) -> dict:
    if not row:
        return {
            "completion_percent": 0,
            "video_progress_percent": 0.0,
            "pdf_progress_percent": 0.0,
            "status": "pending",
        }
    if row.completed_at:
        return {
            "completion_percent": 100,
            "video_progress_percent": 100.0,
            "pdf_progress_percent": 100.0,
            "status": "completed",
        }
    percent = int(round(float(row.completion_percentage or 0)))
    if percent <= 0:
        percent = max(
            int(round(float(row.video_progress_percent or 0))),
            int(round(float(row.pdf_progress_percent or 0))),
        )
    return {
        "completion_percent": min(100, max(0, percent)),
        "video_progress_percent": float(row.video_progress_percent or 0),
        "pdf_progress_percent": float(row.pdf_progress_percent or 0),
        "status": "in_progress" if percent > 0 or row.started_at else "pending",
    }


async def _lesson_out(
    db: AsyncSession,
    lesson: Lesson,
    *,
    unlocked: bool,
    completed: bool,
    progress: StudentLessonProgress | None,
    unit_title: str | None = None,
) -> CourseLessonOut:
    ctype = resolve_lesson_content_type(lesson)
    caps = await build_lesson_capabilities(db, lesson)
    urls = assets_public_urls(lesson)
    prog = _progress_payload(progress)
    if completed:
        prog = {
            "completion_percent": 100,
            "video_progress_percent": 100.0,
            "pdf_progress_percent": 100.0,
            "status": "completed",
        }

    return CourseLessonOut(
        id=lesson.id,
        unit_id=lesson.unit_id,
        unit_title=unit_title,
        title=lesson.title,
        description=lesson.description or lesson.preview,
        video_url=urls.get("video") if unlocked and caps["has_video"] else None,
        pdf_url=urls.get("pdf") if unlocked and caps["has_pdf"] else None,
        homework_url=urls.get("homework") if unlocked and bool(lesson.homework_path) else None,
        sort_order=lesson.sort_order,
        lesson_type=ctype,
        lesson_type_label=LESSON_TYPE_LABELS.get(ctype, ctype),
        status=lesson.status.value if hasattr(lesson.status, "value") else str(lesson.status),
        completed=completed,
        created_at=lesson.created_at.isoformat() if lesson.created_at else None,
        completion_percent=int(prog.get("completion_percent") or 0),
        video_progress_percent=float(prog.get("video_progress_percent") or 0),
        pdf_progress_percent=float(prog.get("pdf_progress_percent") or 0),
        **caps,
    )


async def _units_out(
    db: AsyncSession,
    *,
    lessons: list[Lesson],
    units: list[CourseUnit],
    unlocked: bool,
    completed_ids: set[int],
    progress_by_lesson: dict[int, StudentLessonProgress],
) -> list[StudentCourseUnitOut]:
    units_by_id = {unit.id: unit for unit in units}
    lessons_by_unit: dict[int | None, list[Lesson]] = {unit.id: [] for unit in units}
    unassigned: list[Lesson] = []

    for lesson in lessons:
        if lesson.unit_id in units_by_id:
            lessons_by_unit.setdefault(lesson.unit_id, []).append(lesson)
        else:
            unassigned.append(lesson)

    output: list[StudentCourseUnitOut] = []
    for unit in units:
        unit_lessons = sorted(lessons_by_unit.get(unit.id, []), key=lambda l: (l.sort_order, l.id))
        lesson_out = [
            await _lesson_out(
                db,
                lesson,
                unlocked=unlocked,
                completed=lesson.id in completed_ids,
                progress=progress_by_lesson.get(lesson.id),
                unit_title=unit.title,
            )
            for lesson in unit_lessons
        ]
        total = len(lesson_out)
        done = sum(1 for item in lesson_out if item.completed)
        output.append(
            StudentCourseUnitOut(
                id=unit.id,
                title=unit.title,
                description=unit.description,
                sort_order=unit.sort_order,
                lesson_count=total,
                completed_lesson_count=done if unlocked else 0,
                progress_percent=round((done / total) * 100) if unlocked and total else 0,
                lessons=lesson_out,
            )
        )

    if unassigned:
        lesson_out = [
            await _lesson_out(
                db,
                lesson,
                unlocked=unlocked,
                completed=lesson.id in completed_ids,
                progress=progress_by_lesson.get(lesson.id),
                unit_title="عام",
            )
            for lesson in sorted(unassigned, key=lambda l: (l.sort_order, l.id))
        ]
        total = len(lesson_out)
        done = sum(1 for item in lesson_out if item.completed)
        output.append(
            StudentCourseUnitOut(
                id=None,
                title="عام",
                sort_order=-1,
                lesson_count=total,
                completed_lesson_count=done if unlocked else 0,
                progress_percent=round((done / total) * 100) if unlocked and total else 0,
                lessons=lesson_out,
            )
        )

    return output


def _resume_lesson(
    *,
    course_id: int,
    lessons: list[Lesson],
    units_by_id: dict[int, CourseUnit],
    completed_ids: set[int],
    progress_by_lesson: dict[int, StudentLessonProgress],
) -> StudentCourseResumeLessonOut | None:
    if not lessons:
        return None

    def sort_key(lesson: Lesson) -> tuple[int, int, int]:
        unit = units_by_id.get(lesson.unit_id or -1)
        return ((unit.sort_order if unit else 10_000), lesson.sort_order, lesson.id)

    ordered = sorted(lessons, key=sort_key)

    def activity_ts(row: StudentLessonProgress | None) -> datetime:
        if row is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        return _aware(row.updated_at or row.started_at) or datetime.min.replace(tzinfo=timezone.utc)

    def has_learning_activity(row: StudentLessonProgress | None) -> bool:
        if row is None:
            return False
        return bool(
            row.started_at
            or float(row.completion_percentage or 0) > 0
            or float(row.video_progress_percent or 0) > 0
            or float(row.pdf_progress_percent or 0) > 0
            or row.pdf_opened
            or row.quiz_submitted
        )

    in_progress = [
        (lesson, progress_by_lesson.get(lesson.id))
        for lesson in ordered
        if lesson.id not in completed_ids and has_learning_activity(progress_by_lesson.get(lesson.id))
    ]
    if in_progress:
        lesson, row = max(in_progress, key=lambda item: activity_ts(item[1]))
    else:
        pending = [lesson for lesson in ordered if lesson.id not in completed_ids]
        lesson = pending[0] if pending else ordered[-1]
        row = progress_by_lesson.get(lesson.id)

    unit = units_by_id.get(lesson.unit_id or -1)
    prog = _progress_payload(row)
    if lesson.id in completed_ids:
        prog["status"] = "completed"
        prog["completion_percent"] = 100
    return StudentCourseResumeLessonOut(
        course_id=course_id,
        lesson_id=lesson.id,
        unit_id=lesson.unit_id,
        unit_title=unit.title if unit else ("عام" if lesson.unit_id is None else None),
        title=lesson.title,
        sort_order=lesson.sort_order,
        status=str(prog.get("status") or "pending"),
        completion_percent=int(prog.get("completion_percent") or 0),
    )


async def _build_course_card(
    db: AsyncSession,
    student_id: int,
    course: Course,
    access: dict[int, StudentCourseAccess],
) -> StudentCourseCardOut:
    lessons = await _course_lessons(db, course.id)
    lesson_ids = [l.id for l in lessons]
    completed = await _completed_lesson_ids(db, student_id, lesson_ids)
    total = len(lessons)
    done = len(completed)
    progress = round((done / total) * 100) if total else 0
    row = access.get(course.id)
    unlocked = is_access_active(row)
    status = subscription_lifecycle_status(row)
    activated = _aware(row.activated_at) if row else None
    expires = _aware(row.expires_at) if row else None

    avatar = teacher_avatar_url(course.teacher_profile.image_url)
    return StudentCourseCardOut(
        id=course.id,
        title=course.title,
        subject_name=course.subject.name_ar,
        teacher_name=course.teacher_profile.full_name,
        teacher_image_url=avatar,
        avatar_url=avatar,
        grade=course.grade,
        price=course.price,
        currency=course.currency,
        unlocked=unlocked,
        subscription_status=status,
        access_status=row.access_status if row else None,
        access_source=row.source if row else None,
        enrollment_status=row.enrollment.status if row and row.enrollment else None,
        activated_at=activated.isoformat() if activated else None,
        expires_at=expires.isoformat() if expires else None,
        days_until_expiry=days_until_expiry(row) if row and unlocked else None,
        lock_reason=_lock_reason(row),
        progress_percent=progress if unlocked else 0,
        lesson_count=total,
        completed_lesson_count=done if unlocked else 0,
    )


async def list_student_dashboard(db: AsyncSession, student_id: int) -> StudentDashboardOut:
    profile = await get_student_profile(db, student_id)
    logger.info(
        "list_student_dashboard student_id=%s profile_id=%s grade=%s onboarding_step=%s",
        student_id,
        profile.id,
        profile.grade,
        getattr(profile.onboarding_step, "value", profile.onboarding_step),
    )
    if not profile.grade:
        logger.warning("list_student_dashboard: student_id=%s has no grade on profile", student_id)
        from app.schemas.gamification import GamificationProfileOut
        from app.services.gamification.xp_service import get_gamification_profile

        gamification = await get_gamification_profile(db, student_id)
        return StudentDashboardOut(
            grade=None,
            courses=[],
            unlocked_count=0,
            locked_count=0,
            gamification=GamificationProfileOut(**gamification),
        )

    courses = await _courses_for_grade(db, profile.grade)
    access = await _access_map(db, student_id, [c.id for c in courses])

    cards: list[StudentCourseCardOut] = []
    unlocked_count = 0
    locked_count = 0

    for course in courses:
        card = await _build_course_card(db, student_id, course, access)
        cards.append(card)
        if card.unlocked:
            unlocked_count += 1
        else:
            locked_count += 1

    cards.sort(key=lambda c: (c.unlocked, c.subject_name), reverse=True)

    from app.schemas.gamification import GamificationProfileOut
    from app.services.gamification.xp_service import get_gamification_profile

    gamification = await get_gamification_profile(db, student_id)
    from app.schemas.lesson_completion import LessonCompletionStatsOut
    from app.services.lesson_completion_service import aggregate_lesson_completion_stats

    lesson_stats = await aggregate_lesson_completion_stats(db, student_id)
    return StudentDashboardOut(
        grade=profile.grade,
        courses=cards,
        unlocked_count=unlocked_count,
        locked_count=locked_count,
        gamification=GamificationProfileOut(**gamification),
        lesson_completion=LessonCompletionStatsOut(**lesson_stats),
    )


async def list_subscriptions_catalog(db: AsyncSession, student_id: int) -> SubscriptionsCatalogOut:
    profile = await get_student_profile(db, student_id)
    if not profile.grade:
        return SubscriptionsCatalogOut(grade=None, courses=[], unlocked_count=0, available_count=0)

    courses = await _courses_for_grade(db, profile.grade)
    access = await _access_map(db, student_id, [c.id for c in courses])

    items: list[SubscriptionCourseOut] = []
    unlocked_count = 0

    for course in courses:
        lessons = await _course_lessons(db, course.id)
        counts = _lesson_counts(lessons)
        card = await _build_course_card(db, student_id, course, access)
        if card.unlocked:
            unlocked_count += 1
        items.append(
            SubscriptionCourseOut(
                **card.model_dump(),
                subscription_benefits=_subscription_benefits(lessons, course.subject.name_ar),
                video_count=counts["video"],
                pdf_count=counts["pdf"],
                homework_count=counts["homework"],
                ai_lesson_count=counts["ai"],
            )
        )

    return SubscriptionsCatalogOut(
        grade=profile.grade,
        courses=items,
        unlocked_count=unlocked_count,
        available_count=len(items),
    )


async def get_student_course(
    db: AsyncSession, student_id: int, course_id: int
) -> StudentCourseDetailOut:
    profile = await get_student_profile(db, student_id)

    result = await db.execute(
        select(Course)
        .where(Course.id == course_id, Course.is_active.is_(True))
        .options(
            selectinload(Course.subject),
            selectinload(Course.teacher_profile),
        )
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الدورة غير موجودة")

    if profile.grade and course.grade != profile.grade:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="هذه المادة ليست لصفك")

    if not course.is_published or not course.teacher_profile.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المادة غير متاحة")

    access_result = await db.execute(
        select(StudentCourseAccess).where(
            StudentCourseAccess.student_id == student_id,
            StudentCourseAccess.course_id == course_id,
        ).options(selectinload(StudentCourseAccess.enrollment))
    )
    access = access_result.scalar_one_or_none()
    unlocked = is_access_active(access)
    subscription_status = subscription_lifecycle_status(access)

    lessons = await _course_lessons(db, course_id)
    lesson_ids = [l.id for l in lessons]
    completed = await _completed_lesson_ids(db, student_id, lesson_ids)
    progress_by_lesson = await _progress_map(db, student_id, lesson_ids) if unlocked else {}
    units = await _course_units(db, course_id)
    units_by_id = {unit.id: unit for unit in units}
    total = len(lessons)
    done = len(completed)
    progress = round((done / total) * 100) if total else 0

    unit_out = await _units_out(
        db,
        lessons=lessons,
        units=units,
        unlocked=unlocked,
        completed_ids=completed,
        progress_by_lesson=progress_by_lesson,
    )
    lesson_out = [lesson for unit in unit_out for lesson in unit.lessons]
    resume_lesson = (
        _resume_lesson(
            course_id=course_id,
            lessons=lessons,
            units_by_id=units_by_id,
            completed_ids=completed,
            progress_by_lesson=progress_by_lesson,
        )
        if unlocked
        else None
    )

    activated = _aware(access.activated_at) if access else None
    expires = _aware(access.expires_at) if access else None

    from app.services.messaging_service import _find_existing_course_thread, _linked_parent_ids

    parent_ids = await _linked_parent_ids(db, student_id)
    existing_thread = await _find_existing_course_thread(
        db,
        course_id=course_id,
        student_id=student_id,
        teacher_id=course.teacher_profile.user_id,
    )

    avatar = teacher_avatar_url(course.teacher_profile.image_url)
    return StudentCourseDetailOut(
        id=course.id,
        title=course.title,
        description=course.description,
        subject_name=course.subject.name_ar,
        teacher_name=course.teacher_profile.full_name,
        teacher_image_url=avatar,
        avatar_url=avatar,
        grade=course.grade,
        price=course.price,
        currency=course.currency,
        unlocked=unlocked,
        subscription_status=subscription_status,
        access_status=access.access_status if access else None,
        access_source=access.source if access else None,
        enrollment_status=access.enrollment.status if access and access.enrollment else None,
        activated_at=activated.isoformat() if activated else None,
        expires_at=expires.isoformat() if expires else None,
        days_until_expiry=days_until_expiry(access) if access and unlocked else None,
        lock_reason=_lock_reason(access),
        progress_percent=progress if unlocked else 0,
        lesson_count=total,
        completed_lesson_count=done if unlocked else 0,
        teacher_user_id=course.teacher_profile.user_id,
        teacher_profile_id=course.teacher_profile.id,
        has_linked_parent=bool(parent_ids),
        existing_message_thread_id=existing_thread.id if existing_thread else None,
        lessons=lesson_out,
        units=unit_out,
        resume_lesson=resume_lesson,
    )


async def get_course_teacher_profile(
    db: AsyncSession, student_id: int, course_id: int
) -> StudentCourseTeacherProfileOut:
    profile = await get_student_profile(db, student_id)
    result = await db.execute(
        select(Course)
        .where(Course.id == course_id, Course.is_active.is_(True))
        .options(
            selectinload(Course.subject),
            selectinload(Course.teacher_profile),
        )
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الدورة غير موجودة")
    if profile.grade and course.grade != profile.grade:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="هذه المادة ليست لصفك")
    if not course.is_published or not course.teacher_profile.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المادة غير متاحة")

    tp = course.teacher_profile
    courses_result = await db.execute(
        select(Course.title).where(
            Course.teacher_profile_id == tp.id,
            Course.is_active.is_(True),
            Course.is_published.is_(True),
        ).order_by(Course.grade, Course.title)
    )
    course_titles = list(dict.fromkeys(courses_result.scalars().all()))

    from app.services.teacher_profile_cv_service import load_teacher_profile_cv

    cv = await load_teacher_profile_cv(db, tp.id)
    from app.services.teacher_portfolio_service import load_portfolio_public

    portfolio = await load_portfolio_public(db, tp.id, subject_name=course.subject.name_ar)

    return StudentCourseTeacherProfileOut(
        teacher_user_id=tp.user_id,
        teacher_profile_id=tp.id,
        full_name=tp.full_name,
        image_url=teacher_avatar_url(tp.image_url),
        bio=tp.bio,
        rating=float(tp.rating or 0),
        student_count=int(tp.student_count or 0),
        subject_name=course.subject.name_ar,
        grade=course.grade,
        courses=course_titles,
        qualifications=cv.qualifications,
        teaching_experiences=cv.teaching_experiences,
        achievements=cv.achievements,
        teaching_impact=portfolio["teaching_impact"],
        teaching_philosophy=portfolio["teaching_philosophy"],
        why_study_points=portfolio["why_study_points"],
        academic_statistics=portfolio["academic_statistics"],
        professional_documents=portfolio["professional_documents"],
    )


async def list_student_course_units(
    db: AsyncSession, student_id: int, course_id: int
) -> list[StudentCourseUnitOut]:
    course = await get_student_course(db, student_id, course_id)
    return course.units


async def _load_visible_lesson(db: AsyncSession, lesson_id: int) -> Lesson:
    result = await db.execute(
        select(Lesson).where(Lesson.id == lesson_id).options(
            selectinload(Lesson.assets).selectinload(LessonAsset.media_object)
        )
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الدرس غير موجود")
    sync_lesson_legacy_columns(lesson)
    if not lesson.course_id or not lesson_is_visible(lesson):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الدرس غير متاح")
    course_result = await db.execute(
        select(Course)
        .where(Course.id == lesson.course_id, Course.is_active.is_(True))
        .options(selectinload(Course.teacher_profile))
    )
    course = course_result.scalar_one_or_none()
    if not course or not course.is_published or not course.teacher_profile.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الدرس غير متاح")
    return lesson


async def get_student_lesson(
    db: AsyncSession, student_id: int, lesson_id: int
) -> CourseLessonOut:
    lesson = await _load_visible_lesson(db, lesson_id)
    if not await student_has_lesson_access(db, student_id, lesson):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="المادة مقفلة — اشترك لفتح المحتوى")
    progress_by_lesson = await _progress_map(db, student_id, [lesson.id])
    completed = await _completed_lesson_ids(db, student_id, [lesson.id])
    unit_title: str | None = None
    if lesson.unit_id:
        unit = await db.scalar(
            select(CourseUnit).where(
                CourseUnit.id == lesson.unit_id,
                CourseUnit.course_id == lesson.course_id,
                CourseUnit.is_visible.is_(True),
            )
        )
        unit_title = unit.title if unit else None
    elif lesson.course_id:
        unit_title = "عام"
    return await _lesson_out(
        db,
        lesson,
        unlocked=True,
        completed=lesson.id in completed,
        progress=progress_by_lesson.get(lesson.id),
        unit_title=unit_title,
    )


async def get_lesson_status(
    db: AsyncSession, student_id: int, lesson_id: int
) -> StudentLessonStatusOut:
    lesson = await _load_visible_lesson(db, lesson_id)
    if not await student_has_lesson_access(db, student_id, lesson):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="المادة مقفلة")
    caps = await build_lesson_capabilities(db, lesson)
    return StudentLessonStatusOut(lesson_id=lesson.id, **caps)


async def student_has_lesson_access(db: AsyncSession, student_id: int, lesson: Lesson) -> bool:
    if not lesson.course_id or not lesson_is_visible(lesson):
        return False
    course_result = await db.execute(
        select(Course)
        .where(Course.id == lesson.course_id, Course.is_active.is_(True))
        .options(selectinload(Course.teacher_profile))
    )
    course = course_result.scalar_one_or_none()
    if not course or not course.is_published or not course.teacher_profile.active:
        return False
    access_result = await db.execute(
        select(StudentCourseAccess).where(
            StudentCourseAccess.student_id == student_id,
            StudentCourseAccess.course_id == lesson.course_id,
        ).options(selectinload(StudentCourseAccess.enrollment))
    )
    access = access_result.scalar_one_or_none()
    return is_access_active(access)


async def mark_lesson_complete(db: AsyncSession, student_id: int, lesson_id: int) -> None:
    """Manual completion disabled — use lesson_completion_service after requirements met."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="لا يمكن إكمال الدرس يدوياً — أكمل متطلبات الدرس (فيديو، PDF، اختبار) أولاً",
    )


async def ensure_course_access(db: AsyncSession, student_id: int, course_id: int) -> StudentCourseAccess:
    result = await db.execute(
        select(StudentCourseAccess).where(
            StudentCourseAccess.student_id == student_id,
            StudentCourseAccess.course_id == course_id,
        )
    )
    access = result.scalar_one_or_none()
    if not access:
        access = StudentCourseAccess(
            student_id=student_id,
            course_id=course_id,
            payment_status=PaymentStatus.pending,
        )
        db.add(access)
        await db.flush()
    return access
