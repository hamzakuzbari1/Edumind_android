"""Extended parent dashboard: quiz tracking, attendance, planner progress."""

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivityEventType, StudentActivityEvent
from app.models.lesson import Lesson
from app.models.quiz import QuizAttempt
from app.services.grade_report_service import list_student_grade_reports
from app.services.parent_academic_intelligence_service import build_parent_academic_intelligence
from app.services.parent_insight_service import _quiz_scores_by_subject, build_parent_stats, generate_parent_insights

async def _resolve_student_id(db: AsyncSession, user: "User", student_id: int | None = None) -> int:
    from app.services.parent_link_service import resolve_parent_student_id

    return await resolve_parent_student_id(db, user, student_id)


async def build_quiz_tracking(db: AsyncSession, student_id: int, child_name: str) -> dict:
    result = await db.execute(
        select(QuizAttempt, Lesson.subject, Lesson.title)
        .join(Lesson, Lesson.id == QuizAttempt.lesson_id)
        .where(QuizAttempt.student_id == student_id)
        .order_by(QuizAttempt.created_at.desc())
        .limit(12)
    )
    rows = result.all()
    recent = []
    for attempt, subject, title in rows:
        feedback = []
        if attempt.feedback_json:
            try:
                feedback = json.loads(attempt.feedback_json)
            except Exception:
                pass
        total = len(feedback) if feedback else max(attempt.correct_count, 1)
        score = round((attempt.correct_count / total) * 100) if total else 0
        recent.append(
            {
                "id": attempt.id,
                "subject": subject,
                "lesson_title": title,
                "score": score,
                "date": attempt.created_at.isoformat() if attempt.created_at else None,
                "relative": _relative_ar(attempt.created_at),
            }
        )

    scores_by_subject = await _quiz_scores_by_subject(db, student_id)
    if not scores_by_subject and recent:
        scores_by_subject = {r["subject"]: r["score"] for r in recent if r.get("subject")}

    weak = [s for s, sc in scores_by_subject.items() if sc < 70]
    best = max(scores_by_subject.items(), key=lambda x: x[1]) if scores_by_subject else None

    comments = []
    if recent:
        latest = recent[0]
        comments.append(
            f"ابنك {child_name} حصل على {latest['score']}% في اختبار {latest['subject']}"
        )
    for subj, sc in scores_by_subject.items():
        if sc >= 85:
            comments.append(f"أداء ممتاز في {subj} ({sc}%)")
    if weak:
        comments.append(f"يحتاج دعماً في {weak[0]} — انخفض الأداء هذا الأسبوع")

    chart = [{"subject": s, "score": sc} for s, sc in scores_by_subject.items()]
    if not chart:
        chart = [{"subject": r["subject"], "score": r["score"]} for r in recent[:4]]

    return {
        "recent": recent[:8],
        "chart": chart,
        "weak_subjects": weak,
        "best_subject": {"name": best[0], "score": best[1]} if best else None,
        "average_score": round(sum(scores_by_subject.values()) / len(scores_by_subject)) if scores_by_subject else 0,
        "ai_comments": comments[:4],
    }


async def build_attendance(db: AsyncSession, student_id: int, child_name: str) -> dict:
    from app.services.attendance_service import build_attendance_summary

    return await build_attendance_summary(db, student_id, child_name)


async def build_planner_progress(db: AsyncSession, student_id: int) -> dict:
    from app.services.parent_planner_visibility_service import build_parent_planner_visibility

    data = await build_parent_planner_visibility(db, student_id)
    return {
        **data,
        "weekly_plan": data.get("weekly_plan") or data.get("weekly_plan_legacy") or [],
        "upcoming": data.get("upcoming_tasks") or data.get("upcoming") or [],
    }


_ROUTINE_DAY_LABELS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]


async def build_routine_progress(db: AsyncSession, student_id: int) -> dict:
    """ملخص المخطط والالتزام للأهل — نسبة الالتزام، حالة كل يوم، برنامج اليوم، الامتحانات، المواد الضعيفة."""
    from datetime import datetime, timezone

    from app.services.routine_service import (
        get_or_create_routine_profile,
        get_week_slots,
        get_weak_subjects,
        _get_upcoming_exams,
    )

    profile = await get_or_create_routine_profile(db, student_id)
    week = await get_week_slots(db, profile.id)

    today_index = datetime.now(timezone.utc).weekday()
    today_slots = sorted(week.get(str(today_index), []), key=lambda s: s["start"])

    total_done = 0
    total_missed = 0
    days = []
    for i in range(7):
        slots = week.get(str(i), [])
        completed = sum(1 for s in slots if s["status"] == "completed")
        missed = sum(1 for s in slots if s["status"] == "missed")
        total_done += completed
        total_missed += missed
        if not slots:
            status = "no_plan"
        elif completed == len(slots):
            status = "completed"
        elif missed == len(slots):
            status = "missed"
        elif completed == 0 and missed == 0:
            status = "no_plan"
        else:
            status = "partial"
        sorted_slots = sorted(slots, key=lambda s: s["start"])
        days.append({
            "index": i,
            "label": _ROUTINE_DAY_LABELS[i],
            "status": status,
            "slots": [
                {
                    "start": s["start"],
                    "end": s["end"],
                    "title": s["title"],
                    "subject": s.get("subject"),
                    "status": s["status"],
                }
                for s in sorted_slots
            ],
        })

    tracked = total_done + total_missed
    percent = round((total_done / tracked) * 100) if tracked else 0

    weak = await get_weak_subjects(db, student_id)
    exams = await _get_upcoming_exams(db, student_id)

    earliest_by_subject: dict[str, int] = {}
    for e in exams:
        subject = e["subject"]
        days_left = e["days_left"]
        if subject not in earliest_by_subject or days_left < earliest_by_subject[subject]:
            earliest_by_subject[subject] = days_left
    upcoming_exams = [
        {"subject": subject, "days_left": days_left}
        for subject, days_left in sorted(earliest_by_subject.items(), key=lambda item: item[1])
    ]

    return {
        "onboarding_complete": profile.onboarding_complete,
        "weekly_commitment_percent": percent,
        "days": days,
        "today_label": _ROUTINE_DAY_LABELS[today_index],
        "today_slots": [
            {
                "start": s["start"],
                "end": s["end"],
                "title": s["title"],
                "subject": s.get("subject"),
                "status": s["status"],
            }
            for s in today_slots
        ],
        "upcoming_exams": upcoming_exams,
        "weak_subjects": weak,
    }


def _relative_ar(dt: datetime | None) -> str:
    if not dt:
        return ""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    days = (now - dt).days
    if days == 0:
        return "اليوم"
    if days == 1:
        return "أمس"
    return f"منذ {days} أيام"


async def build_full_parent_dashboard(db: AsyncSession, user, *, student_id: int | None = None) -> dict:
    from app.models.user import User
    from app.schemas.activity import ActivityEventOut
    from app.schemas.parent import LinkedChildOut
    from app.services.activity_service import list_activities

    student_id = await _resolve_student_id(db, user, student_id)
    student_result = await db.execute(select(User).where(User.id == student_id))
    student = student_result.scalar_one_or_none() or user
    child_name = student.name.split()[0] if student.name else "الطالب"

    activity = await list_activities(db, student_id)
    insights = await generate_parent_insights(db, student_id, child_name)
    stats = await build_parent_stats(db, student_id)

    from app.schemas.parent import (
        AttendanceOut,
        CourseProgressOut,
        ParentAcademicIntelligenceOut,
        PlannerProgressOut,
        QuizTrackingOut,
        StudentSubscriptionStatusOut,
    )
    from app.services.parent_subscription_service import list_student_subscription_status

    quiz_data = await build_quiz_tracking(db, student_id, child_name)
    course_progress = [
        CourseProgressOut(**row) for row in await list_student_grade_reports(db, student_id)
    ]
    subscription_rows = await list_student_subscription_status(db, student_id)
    language_placement = await _build_language_placement_summary(db, student_id)
    from app.services.gamification.xp_service import get_gamification_profile

    gamification = await get_gamification_profile(db, student_id)
    academic = await build_parent_academic_intelligence(db, student_id)
    from app.schemas.lesson_completion import ParentLessonProgressOut
    from app.services.parent_lesson_progress_service import list_parent_lesson_progress

    lesson_progress_data = await list_parent_lesson_progress(db, user, student_id=student_id)
    from app.services.parent_student_context_service import build_linked_child_context

    child_ctx = await build_linked_child_context(db, student)
    return {
        "child": LinkedChildOut(**child_ctx),
        "activity": [ActivityEventOut(**a) for a in activity],
        "insights": insights,
        "stats": stats,
        "quiz": QuizTrackingOut(**quiz_data),
        "attendance": AttendanceOut(**await build_attendance(db, student_id, child_name)),
        "planner": PlannerProgressOut(**await build_planner_progress(db, student_id)),
        "course_progress": course_progress,
        "subscriptions": subscription_rows,
        "language_placement": language_placement,
        "gamification": gamification,
        "academic_intelligence": ParentAcademicIntelligenceOut(**academic),
        "lesson_progress": ParentLessonProgressOut(**lesson_progress_data),
    }


async def _build_language_placement_summary(db: AsyncSession, student_id: int) -> dict | None:
    """Language learning summary for parent dashboard."""
    from app.models.language.analytics import LanguageAnalytics
    from app.models.language.catalog import Language
    from app.services.language_analytics_dashboard_service import build_parent_language_analytics_summary
    from app.services.language_analytics_service import get_streak, refresh_language_analytics
    from app.services.language_certificate_service import get_latest_certificate_summary, sync_eligible_certificates

    lang = await db.execute(select(Language).where(Language.code == "en"))
    language = lang.scalar_one_or_none()
    if not language:
        return None

    row = await db.execute(
        select(LanguageAnalytics).where(
            LanguageAnalytics.student_id == student_id,
            LanguageAnalytics.language_id == language.id,
        )
    )
    a = row.scalar_one_or_none()
    if not a:
        return None

    analytics = await refresh_language_analytics(db, student_id=student_id, language_id=language.id)
    await sync_eligible_certificates(db, student_id=student_id, language_id=language.id)
    growth = analytics.skill_growth_json or {}
    streak = await get_streak(db, student_id=student_id, language_id=language.id)
    latest_certificate = await get_latest_certificate_summary(
        db, student_id=student_id, language_id=language.id
    )
    analytics_summary = await build_parent_language_analytics_summary(db, student_id=student_id)

    return {
        "language_code": "en",
        "reading_level": analytics.reading_level.value if analytics.reading_level else None,
        "listening_level": analytics.listening_level.value if analytics.listening_level else None,
        "writing_level": analytics.writing_level.value if analytics.writing_level else None,
        "speaking_level": analytics.speaking_level.value if analytics.speaking_level else None,
        "overall_level": analytics.overall_level_internal.value if analytics.overall_level_internal else None,
        "overall_calculation_method": "bottleneck",
        "skill_growth": {
            "reading": growth.get("reading"),
            "listening": growth.get("listening"),
            "writing": growth.get("writing"),
            "speaking": growth.get("speaking"),
            "vocabulary": growth.get("vocabulary"),
        },
        "vocabulary_count": int(analytics.vocabulary_count or 0),
        "vocabulary_learned": int(growth.get("vocabulary_learned") or 0),
        "current_streak": int(streak.current_streak if streak else 0),
        "longest_streak": int(streak.longest_streak if streak else 0),
        "completed_activities": int(growth.get("completed_activities") or 0),
        "writing_completed": int(growth.get("writing_completed") or 0),
        "speaking_completed": int(growth.get("speaking_completed") or 0),
        "latest_certificate": latest_certificate,
        "language_analytics_summary": analytics_summary,
    }
