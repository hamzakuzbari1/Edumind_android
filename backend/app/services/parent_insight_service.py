"""Rule-based parent insight summaries from student activity data."""

import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivityEventType, StudentActivityEvent
from app.models.quiz import QuizAttempt
from app.models.lesson import Lesson
from app.schemas.activity import ParentInsightOut


async def generate_parent_insights(
    db: AsyncSession,
    student_id: int,
    student_name: str,
) -> list[ParentInsightOut]:
    insights: list[ParentInsightOut] = []
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    # Study activity comparison
    this_week = await _count_events(db, student_id, ActivityEventType.study_session_completed, week_ago)
    last_week = await _count_events(db, student_id, ActivityEventType.study_session_completed, two_weeks_ago, week_ago)
    if this_week < last_week and last_week > 0:
        drop = round(((last_week - this_week) / last_week) * 100)
        insights.append(
            ParentInsightOut(
                id="activity_drop",
                text=f"نشاط الدراسة انخفض مقارنة بالأسبوع الماضي بنسبة {drop}%",
                severity="warning",
                icon="mdi-trending-down",
            )
        )
    elif this_week >= 4:
        insights.append(
            ParentInsightOut(
                id="activity_good",
                text=f"{student_name} يحافظ على نشاط دراسي جيد هذا الأسبوع ({this_week} جلسات)",
                severity="success",
                icon="mdi-trending-up",
            )
        )

    # Quiz performance by subject
    quiz_scores = await _quiz_scores_by_subject(db, student_id)
    if quiz_scores:
        best = max(quiz_scores.items(), key=lambda x: x[1])
        insights.append(
            ParentInsightOut(
                id="best_subject",
                text=f"أفضل أداء كان في {best[0]} ({best[1]}%)",
                severity="success",
                icon="mdi-star",
            )
        )
        weak = [s for s, score in quiz_scores.items() if score < 70]
        if weak:
            subject = weak[0]
            insights.append(
                ParentInsightOut(
                    id="weak_subject",
                    text=f"يبدو أن {student_name} يواجه صعوبة في {subject} هذا الأسبوع",
                    severity="warning",
                    icon="mdi-alert-circle-outline",
                )
            )

    # Recent no-study alert
    no_study = await db.execute(
        select(func.count())
        .select_from(StudentActivityEvent)
        .where(
            StudentActivityEvent.student_id == student_id,
            StudentActivityEvent.event_type == ActivityEventType.no_study_today,
            StudentActivityEvent.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0),
        )
    )
    if no_study.scalar_one() > 0:
        insights.append(
            ParentInsightOut(
                id="no_study",
                text=f"{student_name} لم يدرس اليوم — قد تحتاج متابعة لطيفة",
                severity="info",
                icon="mdi-calendar-remove",
            )
        )

    from app.services.attendance_service import build_attendance_summary

    att = await build_attendance_summary(db, student_id, student_name)
    for i, line in enumerate(att.get("ai_insights", [])[:2]):
        insights.append(
            ParentInsightOut(
                id=f"attendance_{i}",
                text=line,
                severity="info",
                icon="mdi-calendar-check",
            )
        )

    if not insights:
        insights.append(
            ParentInsightOut(
                id="default",
                text=f"تابع تقدم {student_name} — ستظهر الملاحظات الذكية مع زيادة النشاط",
                severity="info",
                icon="mdi-lightbulb-on",
            )
        )

    return insights[:6]


async def _count_events(
    db: AsyncSession,
    student_id: int,
    event_type: ActivityEventType,
    since: datetime,
    until: datetime | None = None,
) -> int:
    q = select(func.count()).select_from(StudentActivityEvent).where(
        StudentActivityEvent.student_id == student_id,
        StudentActivityEvent.event_type == event_type,
        StudentActivityEvent.created_at >= since,
    )
    if until:
        q = q.where(StudentActivityEvent.created_at < until)
    result = await db.execute(q)
    return result.scalar_one()


async def _quiz_scores_by_subject(db: AsyncSession, student_id: int) -> dict[str, int]:
    result = await db.execute(
        select(QuizAttempt, Lesson.subject)
        .join(Lesson, Lesson.id == QuizAttempt.lesson_id)
        .where(QuizAttempt.student_id == student_id)
        .order_by(QuizAttempt.created_at.desc())
        .limit(20)
    )
    rows = result.all()
    subject_scores: dict[str, list[int]] = {}
    for attempt, subject in rows:
        total_q = attempt.correct_count  # need total from feedback
        feedback = []
        if attempt.feedback_json:
            try:
                feedback = json.loads(attempt.feedback_json)
            except Exception:
                pass
        total = len(feedback) if feedback else max(attempt.correct_count, 1)
        pct = round((attempt.correct_count / total) * 100) if total else 0
        subject_scores.setdefault(subject, []).append(pct)

    return {subj: round(sum(scores) / len(scores)) for subj, scores in subject_scores.items()}


async def build_parent_stats(db: AsyncSession, student_id: int) -> dict:
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    sessions = await _count_events(db, student_id, ActivityEventType.study_session_completed, week_ago)
    quizzes = await _count_events(db, student_id, ActivityEventType.quiz_submitted, week_ago)
    quiz_scores = await _quiz_scores_by_subject(db, student_id)
    avg_score = round(sum(quiz_scores.values()) / len(quiz_scores)) if quiz_scores else 0
    return {
        "weekly_sessions": sessions,
        "weekly_quizzes": quizzes,
        "average_score": avg_score,
        "subjects_tracked": len(quiz_scores),
    }
