"""Per-subject performance analytics for AI planner prioritization."""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course_quiz import CourseQuiz, CourseQuizAttempt, CourseQuizAttemptStatus
from app.models.enrollment import StudentCourseAccess
from app.models.lesson import Lesson
from app.models.progress import StudentLessonProgress
from app.models.quiz import QuizAttempt
from app.services.student_courses_service import (
    _completed_lesson_ids,
    _course_lessons,
    _courses_for_grade,
    _access_map,
)
from app.services.subscription_access_service import is_access_active
from app.services.user_status_service import get_student_profile

STRENGTH_STRONG = "strong"
STRENGTH_MEDIUM = "medium"
STRENGTH_WEAK = "weak"

STRENGTH_LABEL_AR = {
    STRENGTH_STRONG: "قوي",
    STRENGTH_MEDIUM: "متوسط",
    STRENGTH_WEAK: "ضعيف",
}


@dataclass
class SubjectPerformance:
    subject_name: str
    course_id: int | None
    average_score: int
    completion_percent: int
    missed_lessons: int
    failed_quizzes: int
    total_lessons: int
    completed_lessons: int
    strength_level: str

    def to_dict(self) -> dict:
        return {
            "subject_name": self.subject_name,
            "course_id": self.course_id,
            "average_score": self.average_score,
            "completion_percent": self.completion_percent,
            "missed_lessons": self.missed_lessons,
            "failed_quizzes": self.failed_quizzes,
            "total_lessons": self.total_lessons,
            "completed_lessons": self.completed_lessons,
            "strength_level": self.strength_level,
            "strength_label": STRENGTH_LABEL_AR.get(self.strength_level, "متوسط"),
        }


def _classify_strength(average_score: int, completion_percent: int) -> str:
    if average_score < 60 or completion_percent < 40:
        return STRENGTH_WEAK
    if average_score >= 80 and completion_percent >= 70:
        return STRENGTH_STRONG
    return STRENGTH_MEDIUM


async def _manual_quiz_stats(db: AsyncSession, student_id: int) -> dict[str, list[int]]:
    from app.models.catalog import Course, Subject

    result = await db.execute(
        select(CourseQuizAttempt.percent, CourseQuizAttempt.score, CourseQuizAttempt.max_score, Course.subject_id)
        .join(CourseQuiz, CourseQuiz.id == CourseQuizAttempt.quiz_id)
        .join(Course, Course.id == CourseQuiz.course_id)
        .where(
            CourseQuizAttempt.student_id == student_id,
            CourseQuizAttempt.status == CourseQuizAttemptStatus.submitted,
        )
    )
    subj_result = await db.execute(select(Subject))
    subjects_by_id = {s.id: s.name_ar for s in subj_result.scalars().all()}

    out: dict[str, list[int]] = {}
    for percent, score, max_score, subject_id in result.all():
        name = subjects_by_id.get(subject_id, "مادة")
        pct = None
        if percent is not None:
            pct = int(round(float(percent)))
        elif max_score and max_score > 0:
            pct = int(round((float(score) / float(max_score)) * 100))
        if pct is not None:
            out.setdefault(name, []).append(pct)
    return out


async def _lesson_quiz_scores_by_subject(db: AsyncSession, student_id: int) -> dict[str, list[int]]:
    result = await db.execute(
        select(QuizAttempt, Lesson.subject)
        .join(Lesson, Lesson.id == QuizAttempt.lesson_id)
        .where(QuizAttempt.student_id == student_id)
    )

    out: dict[str, list[int]] = {}
    for attempt, subject in result.all():
        feedback = []
        if attempt.feedback_json:
            try:
                feedback = json.loads(attempt.feedback_json)
            except Exception:
                pass
        total = len(feedback) if feedback else max(attempt.correct_count, 1)
        pct = round((attempt.correct_count / total) * 100) if total else 0
        out.setdefault(subject, []).append(pct)
    return out


async def compute_subject_analytics(db: AsyncSession, student_id: int) -> list[SubjectPerformance]:
    profile = await get_student_profile(db, student_id)
    if not profile.grade:
        return []

    courses = await _courses_for_grade(db, profile.grade)
    access = await _access_map(db, student_id, [c.id for c in courses])
    lesson_quiz_scores = await _lesson_quiz_scores_by_subject(db, student_id)
    manual_scores = await _manual_quiz_stats(db, student_id)

    rows: list[SubjectPerformance] = []
    for course in courses:
        if not is_access_active(access.get(course.id)):
            continue
        subject_name = course.subject.name_ar
        lessons = await _course_lessons(db, course.id)
        lesson_ids = [l.id for l in lessons]
        completed_ids = await _completed_lesson_ids(db, student_id, lesson_ids)
        total = len(lessons)
        done = len(completed_ids)
        completion = round((done / total) * 100) if total else 0
        missed = max(0, total - done)

        scores = list(lesson_quiz_scores.get(subject_name, []))
        scores.extend(manual_scores.get(subject_name, []))
        avg = round(sum(scores) / len(scores)) if scores else (70 if completion >= 50 else 50)

        failed = sum(1 for s in scores if s < 50)

        strength = _classify_strength(avg, completion)
        rows.append(
            SubjectPerformance(
                subject_name=subject_name,
                course_id=course.id,
                average_score=avg,
                completion_percent=completion,
                missed_lessons=missed,
                failed_quizzes=failed,
                total_lessons=total,
                completed_lessons=done,
                strength_level=strength,
            )
        )

    rows.sort(
        key=lambda r: (
            0 if r.strength_level == STRENGTH_WEAK else 1 if r.strength_level == STRENGTH_MEDIUM else 2,
            -r.missed_lessons,
            r.average_score,
        )
    )
    return rows


def weak_subject_names(analytics: list[SubjectPerformance]) -> list[str]:
    return [a.subject_name for a in analytics if a.strength_level == STRENGTH_WEAK]


def sync_profile_weak_subjects(profile, analytics: list[SubjectPerformance]) -> None:
    import json

    weak = weak_subject_names(analytics)
    profile.weak_subjects_json = json.dumps(weak, ensure_ascii=False)
