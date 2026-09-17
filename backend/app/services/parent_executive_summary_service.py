"""Executive summary for parent AI insights — built from real platform data."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson import Lesson
from app.models.notification import Notification, NotificationType
from app.models.profile import StudentProfile
from app.models.progress import StudentLessonProgress
from app.models.quiz import QuizAttempt
from app.models.student_activity_tracking import StudentEngagementEvent
from app.models.user import User
from app.schemas.activity import ParentInsightOut
from app.services.parent_attendance_analytics_service import (
    _daily_study_minutes,
    _month_end,
    _month_start,
    _pct_change,
    _range_dt,
    _sum_study_seconds,
    _week_start_sunday,
)
from app.services.parent_insight_service import _quiz_scores_by_subject
from app.services.parent_student_context_service import build_linked_child_context, grade_label

LOCAL_TZ_OFFSET_HOURS = 3  # Asia/Damascus approx for parent-facing labels

PARENT_STUDENT_NOTIFICATION_TYPES = {
    NotificationType.parent_student_login.value,
    NotificationType.parent_student_logout.value,
    NotificationType.parent_lesson_completed.value,
    NotificationType.parent_quiz_completed.value,
    NotificationType.parent_low_score.value,
    NotificationType.parent_inactivity.value,
    NotificationType.parent_planner.value,
    NotificationType.parent_alert.value,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _local_hour(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt.hour + LOCAL_TZ_OFFSET_HOURS) % 24


def _format_hour_ar(hour: int) -> str:
    if hour == 0:
        return "12 منتصف الليل"
    if hour < 12:
        return f"{hour} صباحاً"
    if hour == 12:
        return "12 ظهراً"
    return f"{hour - 12} مساءً"


async def _lessons_completed_in_range(
    db: AsyncSession,
    student_id: int,
    start_dt: datetime,
    end_dt: datetime,
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(StudentLessonProgress)
        .where(
            StudentLessonProgress.student_id == student_id,
            StudentLessonProgress.completed_at.is_not(None),
            StudentLessonProgress.completed_at >= start_dt,
            StudentLessonProgress.completed_at < end_dt,
        )
    )
    return int(result.scalar_one() or 0)


async def _pending_lessons_count(db: AsyncSession, student_id: int) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(StudentLessonProgress)
        .where(
            StudentLessonProgress.student_id == student_id,
            StudentLessonProgress.completed_at.is_(None),
        )
    )
    return int(result.scalar_one() or 0)


async def _avg_quiz_score_in_range(
    db: AsyncSession,
    student_id: int,
    start_dt: datetime,
    end_dt: datetime,
) -> int | None:
    result = await db.execute(
        select(QuizAttempt)
        .where(
            QuizAttempt.student_id == student_id,
            QuizAttempt.created_at >= start_dt,
            QuizAttempt.created_at < end_dt,
        )
        .order_by(QuizAttempt.created_at.desc())
        .limit(30)
    )
    attempts = list(result.scalars().all())
    if not attempts:
        return None
    scores: list[int] = []
    for attempt in attempts:
        feedback = []
        if attempt.feedback_json:
            try:
                feedback = json.loads(attempt.feedback_json)
            except Exception:
                pass
        total = len(feedback) if feedback else max(attempt.correct_count, 1)
        scores.append(round((attempt.correct_count / total) * 100) if total else 0)
    return round(sum(scores) / len(scores))


async def _subject_engagement_counts(
    db: AsyncSession,
    student_id: int,
    start_dt: datetime,
    end_dt: datetime,
) -> dict[str, int]:
    result = await db.execute(
        select(Lesson.subject, func.coalesce(func.sum(StudentEngagementEvent.counted_seconds), 0))
        .select_from(StudentEngagementEvent)
        .join(
            Lesson,
            and_(
                StudentEngagementEvent.resource_id == Lesson.id,
                StudentEngagementEvent.resource_type == "lesson",
            ),
        )
        .where(
            StudentEngagementEvent.student_id == student_id,
            StudentEngagementEvent.occurred_at >= start_dt,
            StudentEngagementEvent.occurred_at < end_dt,
        )
        .group_by(Lesson.subject)
    )
    counts: dict[str, int] = {}
    for subject, seconds in result.all():
        if subject:
            counts[subject] = int(seconds or 0)

    if counts:
        return counts

    quiz_rows = await db.execute(
        select(Lesson.subject, func.count())
        .select_from(QuizAttempt)
        .join(Lesson, Lesson.id == QuizAttempt.lesson_id)
        .where(
            QuizAttempt.student_id == student_id,
            QuizAttempt.created_at >= start_dt,
            QuizAttempt.created_at < end_dt,
        )
        .group_by(Lesson.subject)
    )
    for subject, count in quiz_rows.all():
        if subject:
            counts[subject] = int(count or 0) * 60
    return counts


async def _planner_adherence_percent(db: AsyncSession, student_id: int) -> tuple[int | None, dict]:
    from app.services.parent_planner_visibility_service import get_planner_adherence_for_ai

    data = await get_planner_adherence_for_ai(db, student_id)
    rate = data.get("adherence_rate")
    return (int(rate) if rate is not None else None), data


async def _preferred_study_window(
    db: AsyncSession,
    student_id: int,
    start_dt: datetime,
    end_dt: datetime,
) -> tuple[int, int] | None:
    result = await db.execute(
        select(StudentEngagementEvent.occurred_at, StudentEngagementEvent.counted_seconds).where(
            StudentEngagementEvent.student_id == student_id,
            StudentEngagementEvent.occurred_at >= start_dt,
            StudentEngagementEvent.occurred_at < end_dt,
        )
    )
    buckets = [0] * 24
    for occurred_at, counted_seconds in result.all():
        if not occurred_at:
            continue
        h = _local_hour(occurred_at)
        buckets[h] += max(int(counted_seconds or 0), 60)

    best_start = 0
    best_sum = 0
    for h in range(24):
        window = buckets[h] + buckets[(h + 1) % 24]
        if window > best_sum:
            best_sum = window
            best_start = h
    if best_sum <= 0:
        return None
    return best_start, (best_start + 2) % 24


async def _active_days_in_range(
    db: AsyncSession,
    student_id: int,
    start: date,
    end: date,
) -> int:
    by_day = await _daily_study_minutes(db, student_id, start, end)
    return sum(1 for minutes in by_day.values() if minutes > 0)


def _consistency_from_active_days(active_days: int, total_days: int) -> tuple[str, str]:
    ratio = active_days / total_days if total_days else 0
    if ratio >= 5 / 7:
        return "high", "انتظام عالٍ"
    if ratio >= 3 / 7:
        return "medium", "انتظام متوسط"
    return "low", "انتظام منخفض"


def _build_subject_analysis(
    *,
    quiz_scores: dict[str, int],
    engagement: dict[str, int],
    planner_subjects: dict[str, dict],
    mode: str,
) -> dict | None:
    if not quiz_scores and not engagement:
        return None

    if mode == "strength":
        subject = max(quiz_scores.items(), key=lambda x: x[1])[0] if quiz_scores else None
        if not subject and engagement:
            subject = max(engagement.items(), key=lambda x: x[1])[0]
    else:
        subject = min(quiz_scores.items(), key=lambda x: x[1])[0] if quiz_scores else None
        if not subject and engagement:
            subject = min(engagement.items(), key=lambda x: x[1])[0]

    if not subject:
        return None

    reasons: list[str] = []
    avg = quiz_scores.get(subject)
    study_seconds = engagement.get(subject, 0)
    study_minutes = study_seconds // 60

    if mode == "strength":
        if avg is not None:
            reasons.append(f"أعلى متوسط اختبارات ({avg}%)")
        if engagement:
            ranked = sorted(engagement.items(), key=lambda x: x[1], reverse=True)
            rank = next((i + 1 for i, (s, _) in enumerate(ranked) if s == subject), None)
            if rank == 1:
                reasons.append("أعلى مشاركة دراسية")
            elif rank and rank <= 2:
                reasons.append("مشاركة دراسية مرتفعة")
        planner = planner_subjects.get(subject)
        if planner and planner.get("adherence_percent", 0) >= 80:
            reasons.append("التزام جيد بمهام المخطط")
    else:
        if avg is not None and avg < 70:
            reasons.append(f"أدنى متوسط اختبارات ({avg}%)")
        if engagement:
            avg_eng = sum(engagement.values()) / len(engagement) if engagement else 0
            if study_seconds < avg_eng * 0.6:
                reasons.append("وقت دراسة منخفض")
        planner = planner_subjects.get(subject)
        if planner:
            missed = planner.get("total_count", 0) - planner.get("completed_count", 0)
            if missed > 0:
                reasons.append(f"{missed} مهام مخطط غير مكتملة")

    if not reasons:
        if mode == "strength":
            reasons.append("أداء أفضل مقارنة بالمواد الأخرى")
        else:
            reasons.append("يحتاج متابعة إضافية")

    ranked_eng = sorted(engagement.items(), key=lambda x: x[1], reverse=True)
    eng_rank = next((i + 1 for i, (s, _) in enumerate(ranked_eng) if s == subject), None)

    return {
        "subject": subject,
        "reasons": reasons,
        "average_score": avg,
        "study_minutes": study_minutes,
        "engagement_rank": eng_rank,
    }


async def _notification_signals(
    db: AsyncSession,
    parent_id: int | None,
    student_id: int,
) -> dict:
    if not parent_id:
        return {
            "recent_alerts_count": 0,
            "unread_count": 0,
            "has_inactivity_alert": False,
            "has_low_score_alert": False,
            "has_planner_alert": False,
        }

    since = _utcnow() - timedelta(days=7)
    result = await db.execute(
        select(Notification)
        .where(
            Notification.user_id == parent_id,
            Notification.type.in_(PARENT_STUDENT_NOTIFICATION_TYPES),
            Notification.created_at >= since,
            cast(Notification.payload, JSONB)["student_id"].astext == str(student_id),
        )
        .order_by(Notification.created_at.desc())
        .limit(20)
    )
    rows = list(result.scalars().all())
    unread = sum(1 for r in rows if not r.is_read)
    return {
        "recent_alerts_count": len(rows),
        "unread_count": unread,
        "has_inactivity_alert": any(r.type == NotificationType.parent_inactivity.value for r in rows),
        "has_low_score_alert": any(r.type == NotificationType.parent_low_score.value for r in rows),
        "has_planner_alert": any(r.type == NotificationType.parent_planner.value for r in rows),
    }


def _build_risk_alerts(
    *,
    student_name: str,
    period_comparison: dict,
    planner_analytics: dict,
    inactive_days: int | None,
    pending_lessons: int,
    notification_signals: dict,
    weakness: dict | None,
) -> list[ParentInsightOut]:
    risks: list[ParentInsightOut] = []

    study_change = (period_comparison.get("study_time") or {}).get("change_percent")
    if study_change is not None and study_change <= -10:
        risks.append(
            ParentInsightOut(
                id="risk_study_decline",
                text=f"⚠️ نشاط الدراسة انخفض بنسبة {abs(round(study_change))}%",
                severity="warning",
                icon="mdi-trending-down",
                evidence=[
                    f"وقت الدراسة هذا الأسبوع: {(period_comparison.get('study_time') or {}).get('current_value')} ساعة",
                    f"الأسبوع السابق: {(period_comparison.get('study_time') or {}).get('previous_value')} ساعة",
                ],
                data_source="activity_tracking",
            )
        )

    quiz_change = (period_comparison.get("quiz_performance") or {}).get("change_percent")
    if quiz_change is not None and quiz_change <= -5:
        risks.append(
            ParentInsightOut(
                id="risk_grades_decline",
                text=f"⚠️ انخفض متوسط الاختبارات {abs(round(quiz_change))}%",
                severity="warning",
                icon="mdi-chart-line-variant",
                evidence=[
                    f"المتوسط الحالي: {(period_comparison.get('quiz_performance') or {}).get('current_value')}%",
                ],
                data_source="quiz_submissions",
            )
        )

    if inactive_days is not None and inactive_days >= 3:
        risks.append(
            ParentInsightOut(
                id="risk_inactivity",
                text=f"⚠️ لم يسجل {student_name} نشاطاً منذ {inactive_days} أيام",
                severity="error",
                icon="mdi-sleep",
                evidence=[f"آخر نشاط قبل {inactive_days} يوماً"],
                data_source="activity_tracking",
            )
        )

    adherence = planner_analytics.get("adherence_rate")
    overdue = int(planner_analytics.get("overdue_tasks") or 0)
    missed = int(planner_analytics.get("missed_tasks") or 0)
    if adherence is not None and adherence < 60:
        risks.append(
            ParentInsightOut(
                id="risk_planner_neglect",
                text=f"⚠️ الالتزام بالخطة {adherence}% — يحتاج متابعة",
                severity="warning",
                icon="mdi-calendar-alert",
                evidence=[f"مهام متأخرة: {overdue}", f"مهام فائتة: {missed}"],
                data_source="planner_analytics",
            )
        )
    elif overdue >= 2:
        risks.append(
            ParentInsightOut(
                id="risk_planner_overdue",
                text=f"⚠️ {overdue} مهام متأخرة في المخطط",
                severity="warning",
                icon="mdi-calendar-clock",
                evidence=[f"مهام فائتة: {missed}"],
                data_source="planner_analytics",
            )
        )

    if pending_lessons >= 5:
        risks.append(
            ParentInsightOut(
                id="risk_missed_lessons",
                text=f"⚠️ {pending_lessons} دروس لم تُكتمل بعد",
                severity="warning",
                icon="mdi-book-alert-outline",
                evidence=["دروس قيد الانتظار أو قيد التقدم"],
                data_source="lesson_progress",
            )
        )

    if weakness and weakness.get("subject"):
        subj = weakness["subject"]
        risks.append(
            ParentInsightOut(
                id="risk_weak_subject",
                text=f"⚠️ {subj} تحتاج اهتماماً إضافياً",
                severity="warning",
                icon="mdi-alert-circle-outline",
                evidence=weakness.get("reasons") or [],
                data_source="academic_analytics",
            )
        )

    if notification_signals.get("has_inactivity_alert") and not any(r.id == "risk_inactivity" for r in risks):
        risks.append(
            ParentInsightOut(
                id="risk_notif_inactivity",
                text=f"⚠️ تنبيه خمول نشط لـ {student_name}",
                severity="warning",
                icon="mdi-bell-alert",
                evidence=["إشعار خمول من النظام"],
                data_source="notifications",
            )
        )

    return risks[:6]


def _build_recommendations(
    *,
    student_name: str,
    weekly_snapshot: dict,
    period_comparison: dict,
    quiz_scores: dict[str, int],
    adherence: int | None,
    strength: dict | None,
    weakness: dict | None,
    study_behavior: dict,
    planner_analytics: dict,
) -> list[ParentInsightOut]:
    recs: list[ParentInsightOut] = []

    if weakness and weakness.get("subject"):
        subj = weakness["subject"]
        avg = weakness.get("average_score")
        recs.append(
            ParentInsightOut(
                id="increase_weak_subject",
                text=f"زِد وقت دراسة {subj} بمقدار ساعة أسبوعياً.",
                severity="warning",
                icon="mdi-book-open-page-variant",
                evidence=[*(weakness.get("reasons") or []), f"متوسط الاختبارات: {avg}%" if avg else "أداء أضعف"],
                data_source="academic_analytics",
            )
        )

    if strength and strength.get("subject"):
        subj = strength["subject"]
        avg = strength.get("average_score")
        recs.append(
            ParentInsightOut(
                id="maintain_strength",
                text=f"حافظ على الالتزام الحالي في {subj}.",
                severity="success",
                icon="mdi-star",
                evidence=[f"متوسط {avg}%" if avg else "أعلى مشاركة"],
                data_source="academic_analytics",
            )
        )

    if adherence is not None and adherence >= 80:
        recs.append(
            ParentInsightOut(
                id="planner_consistency",
                text="التزام ممتاز بالخطة هذا الأسبوع — استمر على هذا النهج.",
                severity="success",
                icon="mdi-calendar-check",
                evidence=[f"نسبة الالتزام: {adherence}%"],
                data_source="planner_analytics",
            )
        )
    elif adherence is not None and adherence < 60:
        recs.append(
            ParentInsightOut(
                id="planner_review",
                text=f"راجع جدول {student_name} معاً — الالتزام {adherence}%.",
                severity="warning",
                icon="mdi-calendar-alert",
                evidence=[f"مهام متأخرة: {planner_analytics.get('overdue_tasks', 0)}"],
                data_source="planner_analytics",
            )
        )

    quiz_cmp = period_comparison.get("quiz_performance") or {}
    change = quiz_cmp.get("change_percent")
    if change is not None and change <= -5:
        recs.append(
            ParentInsightOut(
                id="review_quizzes",
                text="راجع الاختبارات السابقة قبل الامتحان القادم.",
                severity="warning",
                icon="mdi-clipboard-text-search-outline",
                evidence=[f"انخفاض الأداء {abs(round(change))}%"],
                data_source="quiz_submissions",
            )
        )

    study_cmp = period_comparison.get("study_time") or {}
    study_change = study_cmp.get("change_percent")
    if study_change is not None and study_change >= 10:
        recs.append(
            ParentInsightOut(
                id="study_up",
                text=f"ممتاز — زاد وقت الدراسة {round(study_change)}% عن الأسبوع الماضي.",
                severity="success",
                icon="mdi-clock-plus-outline",
                evidence=[f"{study_cmp.get('current_value')} ساعة هذا الأسبوع"],
                data_source="activity_tracking",
            )
        )
    elif study_behavior.get("consistency_level") == "low":
        recs.append(
            ParentInsightOut(
                id="study_consistency",
                text="حدّد وقتاً يومياً ثابتاً للدراسة لتحسين الانتظام.",
                severity="info",
                icon="mdi-calendar-clock",
                evidence=[
                    f"أيام نشطة: {study_behavior.get('active_days_this_week', 0)}/7",
                    study_behavior.get("preferred_study_hours_label") or "",
                ],
                data_source="activity_tracking",
            )
        )

    if quiz_scores:
        best = max(quiz_scores.items(), key=lambda x: x[1])
        if best[1] >= 85 and not any(r.id == "maintain_strength" for r in recs):
            recs.append(
                ParentInsightOut(
                    id="strong_subject",
                    text=f"أداء قوي في {best[0]} ({best[1]}%) — شجّع على الاستمرار.",
                    severity="success",
                    icon="mdi-star",
                    evidence=[f"متوسط {best[1]}%"],
                    data_source="quiz_submissions",
                )
            )

    return [r for r in recs if r.text][:8]


def _summary_lines(snapshot: dict, planner_analytics: dict) -> list[str]:
    lines: list[str] = []
    if snapshot.get("lessons_completed"):
        lines.append(f"أكمل {snapshot['lessons_completed']} دروس")
    if snapshot.get("study_hours"):
        lines.append(f"درس {snapshot['study_hours']} ساعات")
    if snapshot.get("average_quiz_score") is not None:
        lines.append(f"متوسط علاماته {snapshot['average_quiz_score']}%")
    if snapshot.get("planner_adherence_percent") is not None:
        lines.append(f"التزم بالخطة بنسبة {snapshot['planner_adherence_percent']}%")
    missed = int(planner_analytics.get("missed_tasks") or 0)
    overdue = int(planner_analytics.get("overdue_tasks") or 0)
    if missed == 0 and overdue == 0 and snapshot.get("planner_adherence_percent") is not None:
        lines.append("لم يفوّت أي مهمة دراسية")
    elif missed + overdue > 0:
        lines.append(f"{missed + overdue} مهام مخطط تحتاج متابعة")
    return lines


def _pick_latest_insight(
    risks: list[ParentInsightOut],
    recommendations: list[ParentInsightOut],
) -> ParentInsightOut | None:
    if risks:
        return risks[0]
    if recommendations:
        return recommendations[0]
    return None


async def build_parent_executive_summary(
    db: AsyncSession,
    student_id: int,
    *,
    parent_id: int | None = None,
) -> dict:
    student = await db.get(User, student_id)
    if not student:
        return {"has_data": False}

    ctx = await build_linked_child_context(db, student)
    student_first = ctx["name"].split()[0] if ctx["name"] else "الطالب"
    today = _utcnow().date()

    this_week_start = _week_start_sunday(today, offset=0)
    this_week_end = min(this_week_start + timedelta(days=6), today)
    prev_week_start = _week_start_sunday(today, offset=1)
    prev_week_end = prev_week_start + timedelta(days=6)

    tw_start_dt, tw_end_dt = _range_dt(this_week_start, this_week_end)
    pw_start_dt, pw_end_dt = _range_dt(prev_week_start, prev_week_end)

    days_in_week = (this_week_end - this_week_start).days + 1

    this_week_seconds = await _sum_study_seconds(db, student_id, tw_start_dt, tw_end_dt)
    prev_week_seconds = await _sum_study_seconds(db, student_id, pw_start_dt, pw_end_dt)

    this_lessons = await _lessons_completed_in_range(db, student_id, tw_start_dt, tw_end_dt)
    prev_lessons = await _lessons_completed_in_range(db, student_id, pw_start_dt, pw_end_dt)

    this_quiz_avg = await _avg_quiz_score_in_range(db, student_id, tw_start_dt, tw_end_dt)
    prev_quiz_avg = await _avg_quiz_score_in_range(db, student_id, pw_start_dt, pw_end_dt)

    quiz_scores = await _quiz_scores_by_subject(db, student_id)
    subject_counts = await _subject_engagement_counts(db, student_id, tw_start_dt, tw_end_dt)
    most_active = max(subject_counts.items(), key=lambda x: x[1])[0] if subject_counts else None
    weakest_name = min(quiz_scores.items(), key=lambda x: x[1])[0] if quiz_scores else None
    strongest_name = max(quiz_scores.items(), key=lambda x: x[1])[0] if quiz_scores else most_active

    adherence, planner_analytics = await _planner_adherence_percent(db, student_id)
    prev_adherence = adherence  # planner service is week-scoped; use snapshot delta if available

    planner_subject_map: dict[str, dict] = {}
    for row in planner_analytics.get("subject_breakdown") or []:
        name = row.get("subject_name")
        if name:
            planner_subject_map[name] = {
                "adherence_percent": row.get("adherence_percent", 0),
                "completed_count": row.get("completed_count", 0),
                "total_count": row.get("total_count", 0),
            }

    strength = _build_subject_analysis(
        quiz_scores=quiz_scores,
        engagement=subject_counts,
        planner_subjects=planner_subject_map,
        mode="strength",
    )
    weakness = _build_subject_analysis(
        quiz_scores=quiz_scores,
        engagement=subject_counts,
        planner_subjects=planner_subject_map,
        mode="weakness",
    )

    weekly_snapshot = {
        "lessons_completed": this_lessons,
        "study_hours": round(this_week_seconds / 3600, 1),
        "average_quiz_score": this_quiz_avg,
        "planner_adherence_percent": adherence,
        "missed_planner_tasks": int(planner_analytics.get("missed_tasks") or 0),
        "most_active_subject": most_active,
        "weakest_subject": weakest_name,
        "strongest_subject": strongest_name,
    }

    period_comparison = {
        "period_label": "هذا الأسبوع مقابل الأسبوع السابق",
        "study_time": {
            "label": "وقت الدراسة",
            "current_value": round(this_week_seconds / 3600, 1),
            "previous_value": round(prev_week_seconds / 3600, 1),
            "change_percent": _pct_change(this_week_seconds, prev_week_seconds),
            "unit": "ساعة",
        },
        "lesson_completion": {
            "label": "إكمال الدروس",
            "current_value": float(this_lessons),
            "previous_value": float(prev_lessons),
            "change_percent": _pct_change(this_lessons, prev_lessons),
            "unit": "درس",
        },
        "quiz_performance": {
            "label": "أداء الاختبارات",
            "current_value": float(this_quiz_avg or 0),
            "previous_value": float(prev_quiz_avg or 0),
            "change_percent": (
                _pct_change(this_quiz_avg or 0, prev_quiz_avg or 0)
                if this_quiz_avg is not None or prev_quiz_avg is not None
                else None
            ),
            "unit": "%",
        },
        "planner_adherence": {
            "label": "الالتزام بالخطة",
            "current_value": float(adherence or 0),
            "previous_value": float(prev_adherence or 0),
            "change_percent": None,
            "unit": "%",
        },
    }

    last_30_start = today - timedelta(days=29)
    last_30_start_dt, last_30_end_dt = _range_dt(last_30_start, today)
    last_30_seconds = await _sum_study_seconds(db, student_id, last_30_start_dt, last_30_end_dt)

    prev_30_start = today - timedelta(days=59)
    prev_30_end = today - timedelta(days=30)
    prev_30_start_dt, prev_30_end_dt = _range_dt(prev_30_start, prev_30_end)
    prev_30_seconds = await _sum_study_seconds(db, student_id, prev_30_start_dt, prev_30_end_dt)

    last_7_start = today - timedelta(days=6)
    last_7_start_dt, last_7_end_dt = _range_dt(last_7_start, today)
    last_7_seconds = await _sum_study_seconds(db, student_id, last_7_start_dt, last_7_end_dt)

    prev_7_start = today - timedelta(days=13)
    prev_7_end = today - timedelta(days=7)
    prev_7_start_dt, prev_7_end_dt = _range_dt(prev_7_start, prev_7_end)
    prev_7_seconds = await _sum_study_seconds(db, student_id, prev_7_start_dt, prev_7_end_dt)

    week_totals_hours: list[float] = []
    for offset in range(4):
        ws = _week_start_sunday(today, offset=offset)
        we = ws + timedelta(days=6)
        ws_dt, we_dt = _range_dt(ws, we)
        sec = await _sum_study_seconds(db, student_id, ws_dt, we_dt)
        week_totals_hours.append(round(sec / 3600, 1))

    this_month_start = _month_start(today, offset=0)
    this_month_end = min(_month_end(this_month_start), today)
    tm_start_dt, tm_end_dt = _range_dt(this_month_start, this_month_end)
    this_month_seconds = await _sum_study_seconds(db, student_id, tm_start_dt, tm_end_dt)

    prev_month_start = _month_start(today, offset=1)
    prev_month_end = _month_end(prev_month_start)
    pm_start_dt, pm_end_dt = _range_dt(prev_month_start, prev_month_end)
    prev_month_seconds = await _sum_study_seconds(db, student_id, pm_start_dt, pm_end_dt)

    study_time_averages = {
        "daily_hours": round((last_30_seconds / 30) / 3600, 1),
        "weekly_hours": round(sum(week_totals_hours) / len(week_totals_hours), 1) if week_totals_hours else 0,
        "monthly_hours": round(this_month_seconds / 3600, 1),
        "daily_trend_percent": _pct_change(last_7_seconds // 7, prev_7_seconds // 7),
        "weekly_trend_percent": _pct_change(this_week_seconds, prev_week_seconds),
        "monthly_trend_percent": _pct_change(this_month_seconds, prev_month_seconds),
    }

    active_days = await _active_days_in_range(db, student_id, this_week_start, this_week_end)
    consistency_level, consistency_label = _consistency_from_active_days(active_days, days_in_week)
    preferred = await _preferred_study_window(db, student_id, tw_start_dt, tw_end_dt)
    preferred_label = None
    if preferred:
        start_h, end_h = preferred
        preferred_label = f"{_format_hour_ar(start_h)} - {_format_hour_ar(end_h)}"

    study_behavior = {
        "average_daily_study_hours": round((this_week_seconds / max(days_in_week, 1)) / 3600, 1),
        "preferred_study_hours_label": preferred_label,
        "preferred_study_hours_start": preferred[0] if preferred else None,
        "preferred_study_hours_end": preferred[1] if preferred else None,
        "consistency_level": consistency_level,
        "consistency_label": consistency_label,
        "active_days_this_week": active_days,
        "total_days_this_week": days_in_week,
    }

    profile_result = await db.execute(select(StudentProfile).where(StudentProfile.user_id == student_id))
    profile = profile_result.scalar_one_or_none()
    inactive_days: int | None = None
    if profile and profile.last_activity_at:
        last = profile.last_activity_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        inactive_days = (_utcnow() - last).days

    pending_lessons = await _pending_lessons_count(db, student_id)
    notification_signals = await _notification_signals(db, parent_id, student_id)

    recommendations = _build_recommendations(
        student_name=student_first,
        weekly_snapshot=weekly_snapshot,
        period_comparison=period_comparison,
        quiz_scores=quiz_scores,
        adherence=adherence,
        strength=strength,
        weakness=weakness,
        study_behavior=study_behavior,
        planner_analytics=planner_analytics,
    )

    risk_alerts = _build_risk_alerts(
        student_name=student_first,
        period_comparison=period_comparison,
        planner_analytics=planner_analytics,
        inactive_days=inactive_days,
        pending_lessons=pending_lessons,
        notification_signals=notification_signals,
        weakness=weakness,
    )

    latest_insight = _pick_latest_insight(risk_alerts, recommendations)

    has_data = bool(
        this_week_seconds
        or this_lessons
        or quiz_scores
        or last_30_seconds
        or adherence is not None
        or notification_signals.get("recent_alerts_count")
    )

    return {
        "student_name": ctx["name"],
        "grade_label": ctx.get("grade_label") or grade_label(ctx.get("grade")),
        "academic_status_label": ctx.get("academic_status_label", ""),
        "weekly_snapshot": weekly_snapshot,
        "period_comparison": period_comparison,
        "study_time_averages": study_time_averages,
        "study_behavior": study_behavior,
        "strength_analysis": strength,
        "weakness_analysis": weakness,
        "risk_alerts": risk_alerts,
        "recommendations": recommendations,
        "summary_lines": _summary_lines(weekly_snapshot, planner_analytics),
        "planner_analytics": planner_analytics,
        "notification_signals": notification_signals,
        "latest_insight": latest_insight,
        "has_data": has_data,
    }
