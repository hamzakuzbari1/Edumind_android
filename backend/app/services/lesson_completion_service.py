"""Verified lesson completion — explicit finish, quiz 100%, parent/teacher visibility."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lesson import Lesson
from app.models.progress import StudentLessonProgress
from app.models.quiz import QuizAttempt
from app.services.lesson_assets_service import sync_lesson_legacy_columns
from app.services.lesson_capabilities import build_lesson_capabilities
from app.services.student_courses_service import student_has_lesson_access

VIDEO_COMPLETION_THRESHOLD = 90.0
PDF_COMPLETION_THRESHOLD = 100.0
QUIZ_SCORE_THRESHOLD = 100.0
COMPLETION_TYPE_VERIFIED = "verified"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def lesson_requirements(caps: dict) -> dict:
    has_quiz = bool(caps.get("has_generated_quiz")) and int(caps.get("quiz_question_count") or 0) > 0
    return {
        "requires_video": bool(caps.get("has_video")),
        "requires_pdf": bool(caps.get("has_pdf")),
        "requires_quiz": has_quiz,
        "video_threshold": VIDEO_COMPLETION_THRESHOLD,
        "pdf_threshold": PDF_COMPLETION_THRESHOLD,
        "quiz_score_threshold": QUIZ_SCORE_THRESHOLD,
    }


def _quiz_score_from_attempt(attempt: QuizAttempt) -> int:
    total = 0
    if attempt.feedback_json:
        try:
            total = len(json.loads(attempt.feedback_json))
        except Exception:
            total = 0
    total = total or max(int(attempt.correct_count or 0), 1)
    return int(round((int(attempt.correct_count or 0) / total) * 100))


async def _sync_quiz_data(
    db: AsyncSession, student_id: int, lesson_id: int, progress: StudentLessonProgress
) -> None:
    result = await db.execute(
        select(QuizAttempt)
        .where(QuizAttempt.student_id == student_id, QuizAttempt.lesson_id == lesson_id)
        .order_by(QuizAttempt.id.desc())
        .limit(1)
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        return
    progress.quiz_submitted = True
    progress.quiz_score_percent = float(_quiz_score_from_attempt(attempt))


def _requirement_status(progress: StudentLessonProgress, reqs: dict) -> dict:
    video_met = (
        not reqs["requires_video"]
        or float(progress.video_progress_percent or 0) >= reqs["video_threshold"]
    )
    pdf_met = (
        not reqs["requires_pdf"]
        or (
            bool(progress.pdf_opened)
            and float(progress.pdf_progress_percent or 0) >= reqs["pdf_threshold"]
        )
    )
    quiz_submitted_met = not reqs["requires_quiz"] or bool(progress.quiz_submitted)
    quiz_score_met = (
        not reqs["requires_quiz"]
        or float(progress.quiz_score_percent or 0) >= reqs["quiz_score_threshold"]
    )
    quiz_met = quiz_submitted_met and quiz_score_met
    return {
        "video_met": video_met,
        "pdf_met": pdf_met,
        "quiz_submitted_met": quiz_submitted_met,
        "quiz_score_met": quiz_score_met,
        "quiz_met": quiz_met,
    }


def build_verification_checklist(progress: StudentLessonProgress, reqs: dict, status: dict) -> list[dict]:
    items: list[dict] = []
    if reqs["requires_video"]:
        items.append(
            {
                "key": "video",
                "label": "مشاهدة الفيديو بالكامل (90% على الأقل)",
                "met": status["video_met"],
                "required": True,
            }
        )
    if reqs["requires_pdf"]:
        items.append(
            {
                "key": "pdf_opened",
                "label": "فتح ملف PDF",
                "met": bool(progress.pdf_opened),
                "required": True,
            }
        )
        items.append(
            {
                "key": "pdf_final",
                "label": "الوصول إلى الصفحة الأخيرة",
                "met": status["pdf_met"],
                "required": True,
            }
        )
    if reqs["requires_quiz"]:
        items.append(
            {
                "key": "quiz_submitted",
                "label": "حل جميع الاختبارات",
                "met": status["quiz_submitted_met"],
                "required": True,
            }
        )
        items.append(
            {
                "key": "quiz_score",
                "label": "تحقيق العلامة الكاملة في الكويز (100%)",
                "met": status["quiz_score_met"],
                "required": True,
            }
        )
    return items


def _completion_percent(status: dict, reqs: dict) -> int:
    parts: list[float] = []
    if reqs["requires_video"]:
        parts.append(1.0 if status["video_met"] else 0.0)
    if reqs["requires_pdf"]:
        parts.append(1.0 if status["pdf_met"] else 0.0)
    if reqs["requires_quiz"]:
        parts.append(0.5 if status["quiz_submitted_met"] else 0.0)
        parts.append(0.5 if status["quiz_score_met"] else 0.0)
    if not parts:
        return 0
    return round((sum(parts) / len(parts)) * 100)


def requirements_met(progress: StudentLessonProgress, reqs: dict) -> bool:
    if not any(reqs[k] for k in ("requires_video", "requires_pdf", "requires_quiz")):
        return False
    status = _requirement_status(progress, reqs)
    return status["video_met"] and status["pdf_met"] and status["quiz_met"]


async def _get_lesson(db: AsyncSession, lesson_id: int) -> Lesson:
    result = await db.execute(
        select(Lesson).where(Lesson.id == lesson_id).options(selectinload(Lesson.assets))
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الدرس غير موجود")
    sync_lesson_legacy_columns(lesson)
    return lesson


async def get_or_create_progress(
    db: AsyncSession, student_id: int, lesson_id: int
) -> StudentLessonProgress:
    result = await db.execute(
        select(StudentLessonProgress).where(
            StudentLessonProgress.student_id == student_id,
            StudentLessonProgress.lesson_id == lesson_id,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    row = StudentLessonProgress(student_id=student_id, lesson_id=lesson_id)
    db.add(row)
    await db.flush()
    return row


async def mark_lesson_started(db: AsyncSession, student_id: int, lesson_id: int) -> None:
    lesson = await _get_lesson(db, lesson_id)
    if not await student_has_lesson_access(db, student_id, lesson):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="المادة مقفلة — اشترك لفتح المحتوى")
    progress = await get_or_create_progress(db, student_id, lesson_id)
    if not progress.started_at:
        progress.started_at = _utcnow()
        await db.flush()


async def progress_to_dict(
    db: AsyncSession,
    student_id: int,
    lesson_id: int,
    *,
    progress: StudentLessonProgress | None = None,
    caps: dict | None = None,
) -> dict:
    lesson = await _get_lesson(db, lesson_id)
    if not await student_has_lesson_access(db, student_id, lesson):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="المادة مقفلة — اشترك لفتح المحتوى")
    if caps is None:
        caps = await build_lesson_capabilities(db, lesson)
    reqs = lesson_requirements(caps)
    row = progress or await get_or_create_progress(db, student_id, lesson_id)
    await _sync_quiz_data(db, student_id, lesson_id, row)
    status_flags = _requirement_status(row, reqs)
    checklist = build_verification_checklist(row, reqs, status_flags)
    return {
        "lesson_id": lesson_id,
        "lesson_title": lesson.title,
        "course_id": lesson.course_id,
        "video_progress_percent": round(float(row.video_progress_percent or 0), 1),
        "pdf_progress_percent": round(float(row.pdf_progress_percent or 0), 1),
        "pdf_opened": bool(row.pdf_opened),
        "quiz_submitted": bool(row.quiz_submitted),
        "quiz_score_percent": round(float(row.quiz_score_percent or 0), 1),
        "is_completed": row.is_completed,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "completion_type": row.completion_type,
        "completion_percentage": round(float(row.completion_percentage or 0), 1),
        "completion_percent": _completion_percent(status_flags, reqs),
        "requirements": {**reqs, **status_flags},
        "checklist": checklist,
        "can_verify": requirements_met(row, reqs) and not row.is_completed,
        "lesson_type": _lesson_type_label(caps),
        "newly_completed": False,
    }


def _lesson_type_label(caps: dict) -> str:
    has_video = caps.get("has_video")
    has_pdf = caps.get("has_pdf")
    has_quiz = caps.get("has_generated_quiz")
    if has_video and has_pdf:
        return "mixed"
    if has_pdf and not has_video:
        return "pdf"
    if has_video and not has_pdf:
        return "video"
    if has_quiz:
        return "quiz"
    return "other"


async def update_lesson_progress(
    db: AsyncSession,
    student_id: int,
    lesson_id: int,
    *,
    video_percent: float | None = None,
    pdf_percent: float | None = None,
    pdf_opened: bool | None = None,
) -> dict:
    lesson = await _get_lesson(db, lesson_id)
    if not await student_has_lesson_access(db, student_id, lesson):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="المادة مقفلة — اشترك لفتح المحتوى")

    caps = await build_lesson_capabilities(db, lesson)
    progress = await get_or_create_progress(db, student_id, lesson_id)
    if progress.is_completed:
        return await progress_to_dict(db, student_id, lesson_id, progress=progress, caps=caps)

    now = _utcnow()
    if video_percent is not None:
        progress.video_progress_percent = max(
            float(progress.video_progress_percent or 0),
            min(100.0, float(video_percent)),
        )
        if float(video_percent) > 0:
            progress.video_last_watched_at = now
            if not progress.started_at:
                progress.started_at = now
    if pdf_opened is not None and pdf_opened:
        progress.pdf_opened = True
        if not progress.started_at:
            progress.started_at = now
    if pdf_percent is not None:
        progress.pdf_progress_percent = max(
            float(progress.pdf_progress_percent or 0),
            min(100.0, float(pdf_percent)),
        )
        if float(pdf_percent) > 0 and not progress.started_at:
            progress.started_at = now

    progress.updated_at = now
    await db.flush()
    return await progress_to_dict(db, student_id, lesson_id, progress=progress, caps=caps)


async def on_quiz_submitted_for_lesson(db: AsyncSession, student_id: int, lesson_id: int) -> dict | None:
    lesson = await _get_lesson(db, lesson_id)
    if not await student_has_lesson_access(db, student_id, lesson):
        return None
    progress = await get_or_create_progress(db, student_id, lesson_id)
    if progress.is_completed:
        return await progress_to_dict(db, student_id, lesson_id, progress=progress)
    await _sync_quiz_data(db, student_id, lesson_id, progress)
    progress.updated_at = _utcnow()
    await db.flush()
    return await progress_to_dict(db, student_id, lesson_id, progress=progress)


async def verify_lesson_completion(
    db: AsyncSession, student_id: int, lesson_id: int
) -> dict:
    """Explicit student action — mark verified complete only when all requirements met."""
    lesson = await _get_lesson(db, lesson_id)
    if not await student_has_lesson_access(db, student_id, lesson):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="المادة مقفلة — اشترك لفتح المحتوى")

    caps = await build_lesson_capabilities(db, lesson)
    progress = await get_or_create_progress(db, student_id, lesson_id)
    await _sync_quiz_data(db, student_id, lesson_id, progress)
    reqs = lesson_requirements(caps)
    status_flags = _requirement_status(progress, reqs)
    checklist = build_verification_checklist(progress, reqs, status_flags)

    if progress.is_completed:
        payload = await progress_to_dict(db, student_id, lesson_id, progress=progress, caps=caps)
        return {
            "success": True,
            "message": "تم إكمال هذا الدرس مسبقاً.",
            "checklist": checklist,
            "progress": payload,
        }

    if not requirements_met(progress, reqs):
        return {
            "success": False,
            "message": "لا يمكن إكمال هذا الدرس بعد. أكمل المتطلبات الناقصة أولاً.",
            "checklist": checklist,
            "progress": await progress_to_dict(db, student_id, lesson_id, progress=progress, caps=caps),
        }

    progress.completed_at = _utcnow()
    progress.updated_at = progress.completed_at
    progress.completion_type = COMPLETION_TYPE_VERIFIED
    progress.completion_percentage = 100.0
    await db.flush()

    from app.services.integration_hooks import after_lesson_completed

    await after_lesson_completed(db, student_id, lesson_id)

    payload = await progress_to_dict(db, student_id, lesson_id, progress=progress, caps=caps)
    payload["newly_completed"] = True
    return {
        "success": True,
        "message": "تم إكمال الدرس بنجاح!",
        "checklist": checklist,
        "progress": payload,
    }


async def get_course_lesson_progress_summary(
    db: AsyncSession, student_id: int, lesson_ids: list[int]
) -> dict[int, dict]:
    if not lesson_ids:
        return {}
    result = await db.execute(
        select(StudentLessonProgress).where(
            StudentLessonProgress.student_id == student_id,
            StudentLessonProgress.lesson_id.in_(lesson_ids),
        )
    )
    rows = {r.lesson_id: r for r in result.scalars().all()}
    out: dict[int, dict] = {}
    for lid in lesson_ids:
        row = rows.get(lid)
        if not row:
            out[lid] = {"is_completed": False, "completion_percent": 0, "status": "pending"}
            continue
        if row.is_completed:
            out[lid] = {"is_completed": True, "completion_percent": 100, "status": "completed"}
            continue
        lesson = await _get_lesson(db, lid)
        caps = await build_lesson_capabilities(db, lesson)
        reqs = lesson_requirements(caps)
        await _sync_quiz_data(db, student_id, lid, row)
        status_flags = _requirement_status(row, reqs)
        pct = _completion_percent(status_flags, reqs)
        out[lid] = {
            "is_completed": False,
            "completion_percent": pct,
            "status": "in_progress" if pct > 0 else "pending",
        }
    return out


async def aggregate_lesson_completion_stats(db: AsyncSession, student_id: int) -> dict:
    """Counts completed / in-progress / pending lessons across unlocked courses."""
    from app.services.student_courses_service import (
        _access_map,
        _completed_lesson_ids,
        _course_lessons,
        _courses_for_grade,
        get_student_profile,
    )
    from app.services.subscription_access_service import is_access_active

    profile = await get_student_profile(db, student_id)
    if not profile.grade:
        return {
            "completed_lessons": 0,
            "in_progress_lessons": 0,
            "pending_lessons": 0,
            "total_lessons": 0,
            "completion_rate": 0,
            "current_lesson_title": None,
        }

    courses = await _courses_for_grade(db, profile.grade)
    access = await _access_map(db, student_id, [c.id for c in courses])
    lesson_ids: list[int] = []
    for course in courses:
        if not is_access_active(access.get(course.id)):
            continue
        lessons = await _course_lessons(db, course.id)
        lesson_ids.extend(l.id for l in lessons)

    if not lesson_ids:
        return {
            "completed_lessons": 0,
            "in_progress_lessons": 0,
            "pending_lessons": 0,
            "total_lessons": 0,
            "completion_rate": 0,
            "current_lesson_title": None,
        }

    completed_ids = await _completed_lesson_ids(db, student_id, lesson_ids)
    summary = await get_course_lesson_progress_summary(db, student_id, lesson_ids)
    in_progress = sum(
        1 for lid in lesson_ids if lid not in completed_ids and summary.get(lid, {}).get("status") == "in_progress"
    )
    pending = len(lesson_ids) - len(completed_ids) - in_progress
    total = len(lesson_ids)
    rate = round((len(completed_ids) / total) * 100) if total else 0

    current_title: str | None = None
    for lid in lesson_ids:
        if lid not in completed_ids and summary.get(lid, {}).get("status") == "in_progress":
            lesson = await _get_lesson(db, lid)
            current_title = lesson.title
            break
    if not current_title:
        for lid in lesson_ids:
            if lid not in completed_ids:
                lesson = await _get_lesson(db, lid)
                current_title = lesson.title
                break

    return {
        "completed_lessons": len(completed_ids),
        "in_progress_lessons": in_progress,
        "pending_lessons": pending,
        "total_lessons": total,
        "completion_rate": rate,
        "current_lesson_title": current_title,
    }
