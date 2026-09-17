"""Parent academic intelligence — computed from stored quiz, exam, and lesson data."""

from __future__ import annotations

import json
from statistics import mean

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course_quiz import CourseQuiz, CourseQuizAttempt, CourseQuizAttemptStatus
from app.models.quiz import QuizAttempt
from app.services.student_courses_service import (
    _access_map,
    _completed_lesson_ids,
    _course_lessons,
    _courses_for_grade,
)
from app.services.subscription_access_service import is_access_active
from app.services.user_status_service import get_student_profile

PERFORMANCE_EXCELLENT = "excellent"
PERFORMANCE_GOOD = "good"
PERFORMANCE_NEEDS_IMPROVEMENT = "needs_improvement"

PERFORMANCE_LABEL_AR = {
    PERFORMANCE_EXCELLENT: "ممتاز",
    PERFORMANCE_GOOD: "جيد",
    PERFORMANCE_NEEDS_IMPROVEMENT: "يحتاج تحسين",
}


def _classify_performance(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 85:
        return PERFORMANCE_EXCELLENT
    if score >= 70:
        return PERFORMANCE_GOOD
    return PERFORMANCE_NEEDS_IMPROVEMENT


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return round(mean(values), 1)


def _lesson_quiz_percent(attempt: QuizAttempt) -> float | None:
    feedback: list = []
    if attempt.feedback_json:
        try:
            feedback = json.loads(attempt.feedback_json)
        except Exception:
            feedback = []
    total = len(feedback) if feedback else None
    if not total or total <= 0:
        return None
    return round((attempt.correct_count / total) * 100, 1)


def _exam_percent(percent: float | None, score: float | None, max_score: float | None) -> float | None:
    if percent is not None:
        return round(float(percent), 1)
    if max_score and max_score > 0 and score is not None:
        return round((float(score) / float(max_score)) * 100, 1)
    return None


def _subject_composite(*, quiz_avg: float | None, exam_avg: float | None) -> float | None:
    parts = [v for v in (quiz_avg, exam_avg) if v is not None]
    if not parts:
        return None
    return round(mean(parts), 1)


async def _lesson_quiz_scores_for_course(
    db: AsyncSession,
    student_id: int,
    course_id: int,
) -> list[float]:
    lessons = await _course_lessons(db, course_id)
    lesson_ids = [lesson.id for lesson in lessons]
    if not lesson_ids:
        return []

    result = await db.execute(
        select(QuizAttempt).where(
            QuizAttempt.student_id == student_id,
            QuizAttempt.lesson_id.in_(lesson_ids),
        )
    )
    scores: list[float] = []
    for attempt in result.scalars().all():
        pct = _lesson_quiz_percent(attempt)
        if pct is not None:
            scores.append(pct)
    return scores


async def _exam_scores_for_course(db: AsyncSession, student_id: int, course_id: int) -> list[float]:
    result = await db.execute(
        select(CourseQuizAttempt.percent, CourseQuizAttempt.score, CourseQuizAttempt.max_score)
        .join(CourseQuiz, CourseQuiz.id == CourseQuizAttempt.quiz_id)
        .where(
            CourseQuiz.course_id == course_id,
            CourseQuizAttempt.student_id == student_id,
            CourseQuizAttempt.status.in_(
                [CourseQuizAttemptStatus.submitted, CourseQuizAttemptStatus.graded]
            ),
        )
    )
    scores: list[float] = []
    for percent, score, max_score in result.all():
        pct = _exam_percent(percent, score, max_score)
        if pct is not None:
            scores.append(pct)
    return scores


async def build_parent_academic_intelligence(db: AsyncSession, student_id: int) -> dict:
    profile = await get_student_profile(db, student_id)
    if not profile.grade:
        return _empty_payload("لم يُحدَّد صف الطالب بعد")

    courses = await _courses_for_grade(db, profile.grade)
    access = await _access_map(db, student_id, [c.id for c in courses])

    subjects: list[dict] = []
    all_composite: list[float] = []

    for course in courses:
        if not is_access_active(access.get(course.id)):
            continue

        lessons = await _course_lessons(db, course.id)
        lesson_ids = [lesson.id for lesson in lessons]
        completed_ids = await _completed_lesson_ids(db, student_id, lesson_ids)
        total_lessons = len(lessons)
        completion_rate = round((len(completed_ids) / total_lessons) * 100, 1) if total_lessons else None

        quiz_scores = await _lesson_quiz_scores_for_course(db, student_id, course.id)
        exam_scores = await _exam_scores_for_course(db, student_id, course.id)

        quiz_average = _avg(quiz_scores)
        exam_average = _avg(exam_scores)
        composite = _subject_composite(quiz_avg=quiz_average, exam_avg=exam_average)

        if composite is not None:
            all_composite.append(composite)

        subjects.append(
            {
                "subject_name": course.subject.name_ar,
                "course_id": course.id,
                "course_title": course.title,
                "quiz_average": quiz_average,
                "exam_average": exam_average,
                "completion_rate": completion_rate,
                "quiz_attempts": len(quiz_scores),
                "exam_attempts": len(exam_scores),
                "completed_lessons": len(completed_ids),
                "total_lessons": total_lessons,
                "composite_score": composite,
                "performance_indicator": _classify_performance(composite),
                "performance_label": PERFORMANCE_LABEL_AR.get(_classify_performance(composite) or "", ""),
                "assignments_available": False,
            }
        )

    subjects.sort(
        key=lambda row: (
            row["composite_score"] is None,
            -(row["composite_score"] or 0),
        )
    )

    overall_average = round(mean(all_composite), 1) if all_composite else None
    ranked = [s for s in subjects if s["composite_score"] is not None]
    best_subject = ranked[0] if ranked else None
    weakest_subject = ranked[-1] if len(ranked) > 1 else (ranked[0] if len(ranked) == 1 else None)

    if weakest_subject and best_subject and weakest_subject["course_id"] == best_subject["course_id"]:
        weakest_subject = None

    comparison = [
        {
            "subject_name": row["subject_name"],
            "quiz_average": row["quiz_average"],
            "exam_average": row["exam_average"],
            "completion_rate": row["completion_rate"],
            "composite_score": row["composite_score"],
        }
        for row in subjects
        if row["quiz_average"] is not None
        or row["exam_average"] is not None
        or row["completion_rate"] is not None
    ]

    return {
        "overall_average": overall_average,
        "performance_indicator": _classify_performance(overall_average),
        "performance_label": PERFORMANCE_LABEL_AR.get(_classify_performance(overall_average) or "", ""),
        "best_subject": (
            {
                "subject_name": best_subject["subject_name"],
                "course_id": best_subject["course_id"],
                "composite_score": best_subject["composite_score"],
            }
            if best_subject
            else None
        ),
        "weakest_subject": (
            {
                "subject_name": weakest_subject["subject_name"],
                "course_id": weakest_subject["course_id"],
                "composite_score": weakest_subject["composite_score"],
            }
            if weakest_subject
            else None
        ),
        "subjects": subjects,
        "subject_comparison": comparison,
        "data_sources": {
            "quiz_attempts": sum(s["quiz_attempts"] for s in subjects),
            "exam_attempts": sum(s["exam_attempts"] for s in subjects),
            "lesson_completions": sum(s["completed_lessons"] for s in subjects),
            "assignments_available": False,
        },
        "has_data": bool(comparison),
        "summary": _build_summary(overall_average, best_subject, weakest_subject, len(subjects)),
    }


def _empty_payload(summary: str) -> dict:
    return {
        "overall_average": None,
        "performance_indicator": None,
        "performance_label": "",
        "best_subject": None,
        "weakest_subject": None,
        "subjects": [],
        "subject_comparison": [],
        "data_sources": {
            "quiz_attempts": 0,
            "exam_attempts": 0,
            "lesson_completions": 0,
            "assignments_available": False,
        },
        "has_data": False,
        "summary": summary,
    }


def _build_summary(
    overall: float | None,
    best: dict | None,
    weakest: dict | None,
    subject_count: int,
) -> str:
    if overall is None or subject_count == 0:
        return "لا توجد بيانات أكاديمية كافية بعد — ستظهر التحليلات مع إكمال الاختبارات والدروس"
    parts = [f"المعدل العام {overall}% عبر {subject_count} مادة"]
    if best:
        parts.append(f"أفضل مادة: {best['subject_name']} ({best['composite_score']}%)")
    if weakest:
        parts.append(f"أضعف مادة: {weakest['subject_name']} ({weakest['composite_score']}%)")
    return " — ".join(parts)
