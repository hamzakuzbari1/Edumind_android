"""Parent-facing lesson progress visibility."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.catalog import Course
from app.models.enrollment import StudentCourseAccess
from app.models.lesson import Lesson
from app.models.progress import StudentLessonProgress
from app.models.quiz import QuizAttempt
from app.models.student_activity_tracking import EngagementEventType, StudentEngagementEvent
from app.models.user import User
from app.services.lesson_capabilities import (
    build_lesson_capabilities,
    lesson_is_visible,
    resolve_lesson_content_type,
)
from app.services.lesson_assets_service import paths_from_lesson, sync_lesson_legacy_columns
from app.services.lesson_completion_service import (
    COMPLETION_TYPE_VERIFIED,
    _get_lesson,
    build_verification_checklist,
    get_or_create_progress,
    lesson_requirements,
    progress_to_dict,
    requirements_met,
    _requirement_status,
    _sync_quiz_data,
)
from app.services.parent_link_service import resolve_parent_student_id
from app.services.student_courses_service import student_has_lesson_access
from app.services.subscription_access_service import is_access_active


def _lesson_status(is_completed: bool, completion_percent: int) -> str:
    if is_completed:
        return "completed"
    if completion_percent > 0:
        return "in_progress"
    return "pending"


def _lesson_status_label_ar(status: str) -> str:
    return {"completed": "مكتمل", "in_progress": "قيد التقدم", "pending": "لم يبدأ"}.get(status, status)


def _status_icon(status: str) -> str:
    return {
        "completed": "check",
        "in_progress": "progress",
        "pending": "pending",
    }.get(status, "pending")


_LESSON_TYPE_META: dict[str, tuple[str, str]] = {
    "pdf": ("pdf", "PDF"),
    "video": ("video", "فيديو"),
    "composite": ("composite", "PDF + فيديو"),
    "homework": ("homework", "واجب"),
    "ai_lesson": ("ai_lesson", "درس ذكي"),
    "quiz": ("quiz", "كويز"),
}

_LESSON_TYPE_ICONS: dict[str, str] = {
    "pdf": "mdi-file-pdf-box",
    "video": "mdi-play-circle-outline",
    "composite": "mdi-file-document-multiple-outline",
    "homework": "mdi-clipboard-text-outline",
    "ai_lesson": "mdi-robot-outline",
    "quiz": "mdi-clipboard-check-outline",
    "lesson": "mdi-book-open-page-variant-outline",
}


def _lesson_type_display(lesson: Lesson, caps: dict) -> tuple[str, str, str]:
    content = resolve_lesson_content_type(lesson)
    if caps.get("has_ai_chat"):
        key = "ai_lesson"
    elif caps.get("has_generated_quiz") and content in ("homework", "video") and not caps.get("has_pdf"):
        key = "quiz"
    else:
        key = content if content in _LESSON_TYPE_META else "video"
    _, label = _LESSON_TYPE_META.get(key, ("lesson", "درس"))
    icon = _LESSON_TYPE_ICONS.get(key, _LESSON_TYPE_ICONS["lesson"])
    return key, label, icon


def _last_activity_at(progress: StudentLessonProgress, detail: dict) -> str | None:
    candidates: list[datetime] = []
    for raw in (
        detail.get("completed_at"),
        progress.video_last_watched_at,
        progress.updated_at,
        progress.started_at,
    ):
        if not raw:
            continue
        if isinstance(raw, str):
            try:
                candidates.append(datetime.fromisoformat(raw.replace("Z", "+00:00")))
            except ValueError:
                continue
        elif isinstance(raw, datetime):
            candidates.append(raw)
    if not candidates:
        return None
    latest = max(candidates)
    return latest.isoformat()


async def _teacher_name_map(db: AsyncSession, teacher_ids: set[int]) -> dict[int, str]:
    if not teacher_ids:
        return {}
    result = await db.execute(select(User.id, User.name).where(User.id.in_(teacher_ids)))
    return {row[0]: row[1] for row in result.all() if row[1]}


async def _parent_student_courses(db: AsyncSession, student_id: int) -> list[Course]:
    from app.services.student_courses_service import _courses_for_grade, get_student_profile

    profile = await get_student_profile(db, student_id)
    if not profile.grade:
        return []
    courses = await _courses_for_grade(db, profile.grade)
    access_result = await db.execute(
        select(StudentCourseAccess).where(StudentCourseAccess.student_id == student_id)
    )
    access_map = {a.course_id: a for a in access_result.scalars().all()}
    return [c for c in courses if is_access_active(access_map.get(c.id))]


def _pdf_total_pages(lesson: Lesson) -> int | None:
    paths = paths_from_lesson(lesson)
    pdf_path = paths.get("pdf")
    if not pdf_path:
        return None
    try:
        from app.services.pdf_service import _count_pdf_pages

        settings = get_settings()
        path = Path(pdf_path)
        if not path.is_absolute():
            path = Path(settings.UPLOAD_DIR) / pdf_path.lstrip("/uploads/").lstrip("/")
        return max(1, _count_pdf_pages(path))
    except Exception:
        return None


def _pdf_pages_viewed(total_pages: int | None, progress_percent: float) -> int | None:
    if not total_pages:
        return None
    return max(0, min(total_pages, int(round((progress_percent / 100) * total_pages))))


async def _quiz_stats(db: AsyncSession, student_id: int, lesson_id: int) -> dict:
    result = await db.execute(
        select(QuizAttempt)
        .where(QuizAttempt.student_id == student_id, QuizAttempt.lesson_id == lesson_id)
        .order_by(QuizAttempt.created_at.asc())
    )
    attempts = list(result.scalars().all())
    if not attempts:
        return {"attempt_count": 0, "last_attempt_at": None, "attempts": []}

    import json

    rows: list[dict] = []
    for attempt in attempts:
        feedback = []
        if attempt.feedback_json:
            try:
                feedback = json.loads(attempt.feedback_json)
            except Exception:
                pass
        total = len(feedback) if feedback else max(int(attempt.correct_count or 0), 1)
        score = int(round((int(attempt.correct_count or 0) / total) * 100)) if total else 0
        rows.append(
            {
                "score_percent": score,
                "attempted_at": attempt.created_at.isoformat() if attempt.created_at else None,
            }
        )
    return {
        "attempt_count": len(rows),
        "last_attempt_at": rows[-1]["attempted_at"],
        "attempts": rows,
    }


async def _first_lesson_opened_at(db: AsyncSession, student_id: int, lesson_id: int) -> datetime | None:
    result = await db.execute(
        select(StudentEngagementEvent.occurred_at)
        .where(
            StudentEngagementEvent.student_id == student_id,
            StudentEngagementEvent.resource_type == "lesson",
            StudentEngagementEvent.resource_id == lesson_id,
            StudentEngagementEvent.event_type == EngagementEventType.lesson_opened,
        )
        .order_by(StudentEngagementEvent.occurred_at.asc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row


def _build_missing_requirements(
    progress: StudentLessonProgress,
    detail: dict,
    reqs: dict,
    status_flags: dict,
) -> list[str]:
    missing: list[str] = []
    video_pct = float(detail.get("video_progress_percent") or 0)
    pdf_pct = float(detail.get("pdf_progress_percent") or 0)
    quiz_pct = float(detail.get("quiz_score_percent") or 0)

    if reqs.get("requires_video") and not status_flags.get("video_met"):
        missing.append(f"تقدّم الفيديو {video_pct:.0f}% (مطلوب {reqs['video_threshold']:.0f}%)")
    if reqs.get("requires_pdf") and not progress.pdf_opened:
        missing.append("لم يُفتح ملف PDF")
    elif reqs.get("requires_pdf") and not status_flags.get("pdf_met"):
        missing.append(f"تقدّم PDF {pdf_pct:.0f}% (مطلوب الوصول للصفحة الأخيرة)")
    if reqs.get("requires_quiz") and not status_flags.get("quiz_submitted_met"):
        missing.append("لم يُسلّم الاختبار")
    elif reqs.get("requires_quiz") and not status_flags.get("quiz_score_met"):
        missing.append(f"علامة الاختبار {quiz_pct:.0f}% (مطلوب {reqs['quiz_score_threshold']:.0f}%)")

    reqs_met = requirements_met(progress, reqs)
    if reqs_met and detail.get("completion_type") != COMPLETION_TYPE_VERIFIED:
        missing.append("لم يُضغط زر إنهاء الدرس")
    return missing


def _parent_checklist(
    progress: StudentLessonProgress, reqs: dict, status_flags: dict, detail: dict
) -> list[dict]:
    items = build_verification_checklist(progress, reqs, status_flags)
    if any(reqs.get(k) for k in ("requires_video", "requires_pdf", "requires_quiz")):
        verified = detail.get("completion_type") == COMPLETION_TYPE_VERIFIED
        items.append(
            {
                "key": "completion_button",
                "label": "إنهاء الدرس (زر الإكمال)",
                "met": verified,
                "required": True,
            }
        )
    return items


async def _build_lesson_timeline(
    db: AsyncSession,
    student_id: int,
    lesson_id: int,
    progress: StudentLessonProgress,
    detail: dict,
    quiz_stats: dict,
) -> list[dict]:
    events: list[tuple[datetime, str, str]] = []

    started = progress.started_at or await _first_lesson_opened_at(db, student_id, lesson_id)
    if started:
        events.append((started, "بدأ الدرس", "mdi-play-circle-outline"))

    video_pct = float(detail.get("video_progress_percent") or 0)
    if video_pct > 0:
        when = progress.video_last_watched_at or progress.updated_at
        if when:
            events.append(
                (when, f"شاهد {video_pct:.0f}% من الفيديو", "mdi-play-circle")
            )

    pdf_pct = float(detail.get("pdf_progress_percent") or 0)
    if pdf_pct > 0 and progress.updated_at:
        events.append(
            (progress.updated_at, f"تقدّم PDF {pdf_pct:.0f}%", "mdi-file-document-outline")
        )

    for attempt in quiz_stats.get("attempts") or []:
        if attempt.get("attempted_at"):
            dt = datetime.fromisoformat(attempt["attempted_at"].replace("Z", "+00:00"))
            events.append(
                (
                    dt,
                    f"حصل على {attempt['score_percent']}% في الاختبار",
                    "mdi-clipboard-check-outline",
                )
            )

    if progress.completed_at:
        events.append((progress.completed_at, "أكمل الدرس", "mdi-check-circle"))

    events.sort(key=lambda e: e[0])
    return [
        {
            "date": dt.astimezone(timezone.utc).date().isoformat(),
            "datetime": dt.isoformat(),
            "label": label,
            "icon": icon,
        }
        for dt, label, icon in events
    ]


async def list_parent_lesson_progress(
    db: AsyncSession, parent_user, *, student_id: int | None = None
) -> dict:
    sid = await resolve_parent_student_id(db, parent_user, student_id)
    courses = await _parent_student_courses(db, sid)
    course_blocks: list[dict] = []
    totals = {"completed": 0, "in_progress": 0, "pending": 0}

    for course in courses:
        result = await db.execute(
            select(Lesson)
            .where(Lesson.course_id == course.id)
            .options(selectinload(Lesson.assets))
            .order_by(Lesson.sort_order, Lesson.id)
        )
        lessons_raw = list(result.scalars().all())
        teacher_ids = {l.teacher_id for l in lessons_raw if l.teacher_id}
        teachers = await _teacher_name_map(db, teacher_ids)

        lessons_out: list[dict] = []
        course_completed = 0
        course_in_progress = 0
        course_pending = 0
        for lesson in lessons_raw:
            sync_lesson_legacy_columns(lesson)
            if not lesson_is_visible(lesson):
                continue
            if not await student_has_lesson_access(db, sid, lesson):
                continue
            progress = await get_or_create_progress(db, sid, lesson.id)
            caps = await build_lesson_capabilities(db, lesson)
            detail = await progress_to_dict(db, sid, lesson.id, progress=progress, caps=caps)
            pct = int(detail.get("completion_percent") or 0)
            st = _lesson_status(bool(detail.get("is_completed")), pct)
            totals[st] = totals.get(st, 0) + 1
            if st == "completed":
                course_completed += 1
            elif st == "in_progress":
                course_in_progress += 1
            else:
                course_pending += 1

            type_key, type_label, type_icon = _lesson_type_display(lesson, caps)
            title = (lesson.title or "").strip() or f"درس {lesson.id}"
            teacher_name = teachers.get(lesson.teacher_id) if lesson.teacher_id else None

            lessons_out.append(
                {
                    "lesson_id": lesson.id,
                    "lesson_title": title,
                    "course_id": course.id,
                    "course_title": course.title,
                    "subject_name": course.subject.name_ar if course.subject else "",
                    "status": st,
                    "status_label": _lesson_status_label_ar(st),
                    "status_icon": _status_icon(st),
                    "completion_percent": pct,
                    "completion_quality": "verified"
                    if detail.get("completion_type") == COMPLETION_TYPE_VERIFIED
                    else ("partial" if pct > 0 else "none"),
                    "is_verified": detail.get("completion_type") == COMPLETION_TYPE_VERIFIED,
                    "completed_at": detail.get("completed_at"),
                    "last_activity_at": _last_activity_at(progress, detail),
                    "teacher_name": teacher_name,
                    "lesson_type": type_key,
                    "lesson_type_label": type_label,
                    "lesson_type_icon": type_icon,
                }
            )
        if lessons_out:
            total_in_course = len(lessons_out)
            course_blocks.append(
                {
                    "course_id": course.id,
                    "course_title": course.title,
                    "subject_name": course.subject.name_ar if getattr(course, "subject", None) else "",
                    "completed_count": course_completed,
                    "in_progress_count": course_in_progress,
                    "pending_count": course_pending,
                    "total_lessons": total_in_course,
                    "progress_percent": round((course_completed / total_in_course) * 100)
                    if total_in_course
                    else 0,
                    "lessons": lessons_out,
                }
            )

    total_lessons = sum(totals.values())
    return {
        "student_id": sid,
        "courses": course_blocks,
        "summary": {
            "completed_lessons": totals.get("completed", 0),
            "in_progress_lessons": totals.get("in_progress", 0),
            "pending_lessons": totals.get("pending", 0),
            "total_lessons": total_lessons,
            "completion_rate": round((totals.get("completed", 0) / total_lessons) * 100)
            if total_lessons
            else 0,
            "current_lesson_title": next(
                (
                    l["lesson_title"]
                    for c in course_blocks
                    for l in c["lessons"]
                    if l["status"] == "in_progress"
                ),
                next(
                    (
                        l["lesson_title"]
                        for c in course_blocks
                        for l in c["lessons"]
                        if l["status"] == "pending"
                    ),
                    None,
                ),
            ),
        },
    }


async def get_parent_lesson_detail(
    db: AsyncSession, parent_user, lesson_id: int, *, student_id: int | None = None
) -> dict:
    sid = await resolve_parent_student_id(db, parent_user, student_id)
    lesson = await _get_lesson(db, lesson_id)
    if not await student_has_lesson_access(db, sid, lesson):
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="لا يمكن عرض هذا الدرس")

    course_result = await db.execute(
        select(Course).where(Course.id == lesson.course_id).options(selectinload(Course.subject))
    )
    course = course_result.scalar_one_or_none()

    teacher_name = "—"
    if lesson.teacher_id:
        teacher = await db.get(User, lesson.teacher_id)
        if teacher and teacher.name:
            teacher_name = teacher.name

    progress = await get_or_create_progress(db, sid, lesson_id)
    caps = await build_lesson_capabilities(db, lesson)
    reqs = lesson_requirements(caps)
    detail = await progress_to_dict(db, sid, lesson_id, progress=progress, caps=caps)
    await _sync_quiz_data(db, sid, lesson_id, progress)
    status_flags = _requirement_status(progress, reqs)
    quiz_stats = await _quiz_stats(db, sid, lesson_id)

    st = _lesson_status(detail.get("is_completed"), int(detail.get("completion_percent") or 0))
    is_verified = detail.get("completion_type") == COMPLETION_TYPE_VERIFIED
    pdf_total = _pdf_total_pages(lesson)
    pdf_viewed = _pdf_pages_viewed(pdf_total, float(detail.get("pdf_progress_percent") or 0))
    missing = _build_missing_requirements(progress, detail, reqs, status_flags)
    checklist = _parent_checklist(progress, reqs, status_flags, detail)
    timeline = await _build_lesson_timeline(db, sid, lesson_id, progress, detail, quiz_stats)

    verification_label = "مكتمل موثّق" if is_verified else ("غير مكتمل" if st != "pending" else "لم يبدأ")

    return {
        "lesson_id": lesson_id,
        "lesson_title": lesson.title,
        "course_id": lesson.course_id,
        "course_title": course.title if course else "",
        "subject_name": course.subject.name_ar if course and course.subject else "",
        "teacher_name": teacher_name,
        "video_progress_percent": detail["video_progress_percent"],
        "video_last_watched_at": (
            progress.video_last_watched_at.isoformat() if progress.video_last_watched_at else None
        ),
        "pdf_progress_percent": detail["pdf_progress_percent"],
        "pdf_total_pages": pdf_total,
        "pdf_pages_viewed": pdf_viewed,
        "pdf_opened": bool(progress.pdf_opened),
        "quiz_score_percent": detail["quiz_score_percent"],
        "quiz_attempt_count": quiz_stats["attempt_count"],
        "quiz_last_attempt_at": quiz_stats["last_attempt_at"],
        "completion_status": _lesson_status_label_ar(st),
        "completion_status_code": st,
        "is_verified": is_verified,
        "verification_status": "verified" if is_verified else "incomplete",
        "verification_status_label": verification_label,
        "completed_at": detail.get("completed_at"),
        "started_at": progress.started_at.isoformat() if progress.started_at else None,
        "completion_type": detail.get("completion_type"),
        "completion_percent": detail.get("completion_percent"),
        "completion_quality": "verified" if is_verified else ("partial" if st == "in_progress" else "none"),
        "checklist": checklist,
        "missing_requirements": missing,
        "requirements": detail.get("requirements") or {},
        "timeline": timeline,
    }
