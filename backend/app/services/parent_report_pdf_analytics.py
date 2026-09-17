"""Extended analytics payload for parent PDF dashboard reports."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student_activity_tracking import EngagementEventType, StudentEngagementEvent
from app.services.grade_report_service import list_student_grade_reports
from app.services.parent_attendance_analytics_service import (
    _daily_study_minutes,
    _range_dt,
    _sum_study_seconds,
    _week_start_sunday,
)
from app.services.parent_historical_reports_service import _avg_quiz_score

AR_WEEKDAYS_SHORT = ["أ", "إ", "ث", "أ", "خ", "ج", "س"]


async def _weekly_study_hours(
    db: AsyncSession, student_id: int, end: date, *, weeks: int = 8
) -> list[dict]:
    buckets: list[dict] = []
    for offset in range(weeks - 1, -1, -1):
        ws = _week_start_sunday(end, offset=offset)
        we = min(ws + timedelta(days=6), end)
        if ws > end:
            continue
        seconds = await _sum_study_seconds(db, student_id, *_range_dt(ws, we))
        buckets.append(
            {
                "label": ws.strftime("%m/%d"),
                "date": ws.isoformat(),
                "value": round(seconds / 3600, 1),
            }
        )
    return buckets


async def _weekly_grade_trend(
    db: AsyncSession, student_id: int, end: date, *, weeks: int = 8
) -> list[dict]:
    buckets: list[dict] = []
    for offset in range(weeks - 1, -1, -1):
        ws = _week_start_sunday(end, offset=offset)
        we = ws + timedelta(days=6)
        if ws > end:
            continue
        avg = await _avg_quiz_score(db, student_id, *_range_dt(ws, we))
        buckets.append(
            {
                "label": ws.strftime("%m/%d"),
                "date": ws.isoformat(),
                "value": float(avg or 0),
            }
        )
    return buckets


async def _activity_breakdown(
    db: AsyncSession,
    student_id: int,
    start_dt,
    end_dt,
) -> dict[str, float]:
    result = await db.execute(
        select(
            StudentEngagementEvent.event_type,
            func.coalesce(func.sum(StudentEngagementEvent.counted_seconds), 0).label("seconds"),
        )
        .where(
            StudentEngagementEvent.student_id == student_id,
            StudentEngagementEvent.occurred_at >= start_dt,
            StudentEngagementEvent.occurred_at < end_dt,
        )
        .group_by(StudentEngagementEvent.event_type)
    )
    raw: dict[str, int] = {}
    for row in result.all():
        key = row.event_type.value if hasattr(row.event_type, "value") else str(row.event_type)
        raw[key] = int(row.seconds or 0)

    lessons = sum(
        raw.get(k, 0)
        for k in (
            EngagementEventType.lesson_opened.value,
            EngagementEventType.lesson_viewed.value,
            EngagementEventType.lesson_completed.value,
        )
    )
    quizzes = sum(
        raw.get(k, 0)
        for k in (EngagementEventType.quiz_started.value, EngagementEventType.quiz_submitted.value)
    )
    ai_chat = raw.get(EngagementEventType.messaging_activity.value, 0)
    video = int(lessons * 0.35) if lessons else 0
    lessons_net = max(lessons - video, 0)
    planner = raw.get(EngagementEventType.planner_activity.value, 0)
    navigation = raw.get(EngagementEventType.page_navigation.value, 0)
    other = max(navigation + planner, 0)

    total = lessons_net + quizzes + ai_chat + video + other
    if total <= 0:
        return {
            "lessons": 0.0,
            "quizzes": 0.0,
            "ai_chat": 0.0,
            "video": 0.0,
            "other": 0.0,
        }

    to_min = lambda s: round(s / 60, 1)
    return {
        "lessons": to_min(lessons_net),
        "quizzes": to_min(quizzes),
        "ai_chat": to_min(ai_chat),
        "video": to_min(video),
        "other": to_min(other),
    }


async def _attendance_heatmap(
    db: AsyncSession, student_id: int, end: date, *, weeks: int = 6
) -> list[dict]:
    start = _week_start_sunday(end, offset=weeks - 1)
    by_day = await _daily_study_minutes(db, student_id, start, end)
    cells: list[dict] = []
    cursor = start
    while cursor <= end:
        minutes = by_day.get(cursor, 0)
        cells.append(
            {
                "date": cursor.isoformat(),
                "weekday": AR_WEEKDAYS_SHORT[(cursor.weekday() + 1) % 7],
                "minutes": minutes,
                "level": _heat_level(minutes),
            }
        )
        cursor += timedelta(days=1)
    return cells


def _heat_level(minutes: int) -> int:
    if minutes <= 0:
        return 0
    if minutes < 15:
        return 1
    if minutes < 45:
        return 2
    if minutes < 90:
        return 3
    return 4


def _attendance_rate(sessions: list[dict], start: date, end: date) -> float:
    span_days = max((end - start).days + 1, 1)
    active_days = len({s.get("date") for s in sessions if s.get("date")})
    return round(min(100.0, (active_days / span_days) * 100), 1)


def _pct_delta(current: float, previous: float) -> float | None:
    if previous <= 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def _trend_line(current: float, previous: float, label: str) -> str | None:
    delta = _pct_delta(current, previous)
    if delta is None:
        return None
    if abs(delta) < 3:
        return f"● {label} مستقر"
    if delta > 0:
        return f"↑ {label} زاد بنسبة {delta:.0f}%"
    return f"↓ {label} انخفض بنسبة {abs(delta):.0f}%"


def _weekly_attendance_scores(heatmap: list[dict]) -> list[float]:
    """Active days per week as percentage (0-100)."""
    if not heatmap:
        return []
    by_week: dict[str, list[int]] = {}
    for cell in heatmap:
        d = cell.get("date", "")
        week_key = d[:10]  # group by week start approx - use Sunday
        from datetime import date as dt

        day = dt.fromisoformat(d)
        ws = _week_start_sunday(day, offset=0)
        key = ws.isoformat()
        by_week.setdefault(key, []).append(int(cell.get("minutes") or 0))
    scores: list[float] = []
    for key in sorted(by_week.keys()):
        mins = by_week[key]
        active = sum(1 for m in mins if m > 0)
        scores.append(round((active / max(len(mins), 1)) * 100, 1))
    return scores


def build_weekly_performance(
    study: list[dict],
    grades: list[dict],
    lessons: list[dict],
    heatmap: list[dict],
) -> list[dict]:
    att_scores = _weekly_attendance_scores(heatmap)
    weeks: list[dict] = []
    n = min(len(study), len(grades), len(lessons), 8)
    for i in range(1, n):
        lines: list[str] = []
        for label, series, name in [
            ("وقت الدراسة", study, "study"),
            ("الدرجات", grades, "grades"),
            ("إكمال الدروس", lessons, "lessons"),
        ]:
            if i < len(series):
                line = _trend_line(
                    float(series[i].get("value") or 0),
                    float(series[i - 1].get("value") or 0),
                    label,
                )
                if line:
                    lines.append(line)
        if i < len(att_scores):
            line = _trend_line(att_scores[i], att_scores[i - 1], "الحضور")
            if line:
                lines.append(line)
        weeks.append(
            {
                "label": f"أسبوع {study[i].get('label', i + 1)}",
                "date": study[i].get("date", ""),
                "lines": lines,
            }
        )
    return weeks[-6:]


def build_performance_timeline(study: list[dict], grades: list[dict]) -> dict:
    if not study:
        return {"best_week": "—", "worst_week": "—", "most_improved_week": "—"}
    active = [s for s in study if float(s.get("value") or 0) > 0]
    best = max(study, key=lambda x: float(x.get("value") or 0))
    worst_pool = active or study
    worst = min(worst_pool, key=lambda x: float(x.get("value") or 0))
    best_improve = {"label": "—", "delta": -999.0}
    for i in range(1, len(study)):
        prev = float(study[i - 1].get("value") or 0)
        cur = float(study[i].get("value") or 0)
        delta = cur - prev
        if delta > best_improve["delta"]:
            best_improve = {"label": study[i].get("label", ""), "delta": delta}
    return {
        "best_week": best.get("label", "—"),
        "worst_week": worst.get("label", "—"),
        "most_improved_week": best_improve["label"],
    }


def build_risk_indicators(report: dict, analytics: dict) -> list[dict]:
    risks: list[dict] = []
    cmp_ = report.get("comparison") or {}
    study_chg = (cmp_.get("study_time") or {}).get("change_percent")
    grade_chg = (cmp_.get("grades") or {}).get("change_percent")
    att = analytics.get("attendance_rate") or 0
    grades = analytics.get("weekly_grades") or []

    if grade_chg is not None and grade_chg <= -8:
        risks.append(
            {
                "title": "تراجع في الدرجات",
                "message": f"متوسط الدرجات انخفض بنسبة {abs(grade_chg):.0f}% عن الفترة السابقة.",
            }
        )
    if study_chg is not None and study_chg <= -15:
        risks.append(
            {
                "title": "انخفاض وقت الدراسة",
                "message": f"وقت الدراسة أقل بنسبة {abs(study_chg):.0f}% — قد يحتاج الطالب دعماً.",
            }
        )
    if att < 45:
        risks.append(
            {
                "title": "ضعف في الحضور",
                "message": f"معدل الحضور {att:.0f}% — يُنصح بمتابعة الانتظام اليومي.",
            }
        )
    if len(grades) >= 3:
        last3 = [float(g.get("value") or 0) for g in grades[-3:]]
        if last3[0] > last3[1] > last3[2] and last3[0] > 0:
            risks.append(
                {
                    "title": "نشاط غير منتظم",
                    "message": "تذبذب في النشاط خلال الأسابيع الأخيرة — حاول تثبيت عادات يومية.",
                }
            )
    if not risks:
        risks.append({"title": "لا مخاطر حرجة", "message": "لا توجد مؤشرات خطر بارزة في هذه الفترة."})
    return risks[:4]


def build_achievements(report: dict, analytics: dict) -> list[dict]:
    study = analytics.get("weekly_study_hours") or []
    courses = analytics.get("course_progress") or []
    breakdown = analytics.get("activity_breakdown") or {}
    grades = analytics.get("weekly_grades") or []
    heatmap = analytics.get("attendance_heatmap") or []

    achievements: list[dict] = []
    if study:
        best = max(study, key=lambda x: float(x.get("value") or 0))
        achievements.append(
            {
                "title": "أعلى أسبوع دراسة",
                "value": f"{best.get('label', '')} — {best.get('value', 0)} ساعة",
            }
        )
    streak = 0
    best_streak = 0
    for cell in heatmap:
        if int(cell.get("minutes") or 0) > 0:
            streak += 1
            best_streak = max(best_streak, streak)
        else:
            streak = 0
    if best_streak:
        achievements.append({"title": "أطول سلسلة نشاط", "value": f"{best_streak} أيام متتالية"})
    if courses:
        top = max(courses, key=lambda c: float(c.get("completion") or 0))
        achievements.append(
            {
                "title": "أكثر دورة نشاطاً",
                "value": f"{top.get('title', '')} — {top.get('completion', 0):.0f}% إكمال",
            }
        )
    if grades:
        best_g = max(grades, key=lambda g: float(g.get("value") or 0))
        if float(best_g.get("value") or 0) > 0:
            achievements.append(
                {"title": "أفضل نتيجة اختبار", "value": f"{best_g.get('label', '')} — {best_g.get('value', 0):.0f}%"}
            )
    ai_min = breakdown.get("ai_chat") or 0
    if ai_min > 0:
        achievements.append({"title": "تفاعل التعلم الذكي", "value": f"{ai_min:.0f} دقيقة في المحادثة الذكية"})
    if not achievements:
        achievements.append({"title": "بداية رائعة", "value": "ستظهر الإنجازات مع زيادة النشاط"})
    return achievements[:5]


def build_narrative_summary(report: dict, analytics: dict) -> str:
    cmp_ = report.get("comparison") or {}
    study_chg = (cmp_.get("study_time") or {}).get("change_percent")
    grade_chg = (cmp_.get("grades") or {}).get("change_percent")
    planner = (cmp_.get("planner_adherence") or {}).get("current_value") or 0
    att = analytics.get("attendance_rate") or 0
    parts: list[str] = ["خلال آخر 8 أسابيع،"]

    if study_chg is not None:
        if study_chg >= 10:
            parts.append(f"زاد وقت الدراسة بنسبة {study_chg:.0f}%،")
        elif study_chg <= -10:
            parts.append(f"انخفض وقت الدراسة بنسبة {abs(study_chg):.0f}%،")
        else:
            parts.append("بقي وقت الدراسة مستقراً،")

    if att >= 60:
        parts.append("والحضور منتظم،")
    else:
        parts.append("والحضور يحتاج متابعة،")

    if grade_chg is not None and grade_chg >= 5:
        parts.append("وتحسّنت نتائج الاختبارات تدريجياً.")
    elif grade_chg is not None and grade_chg <= -5:
        parts.append("وانخفضت نتائج الاختبارات قليلاً.")
    else:
        parts.append("وبقيت نتائج الاختبارات مستقرة.")

    timeline = analytics.get("performance_timeline") or {}
    if timeline.get("most_improved_week") and timeline["most_improved_week"] != "—":
        parts.append(f" أقوى نمو كان في أسبوع {timeline['most_improved_week']}.")

    if planner < 50:
        parts.append(" المجال الأهم للمتابعة: الالتزام بالخطة الدراسية.")
    elif planner >= 80:
        parts.append(" الالتزام بالخطة ممتاز.")

    return " ".join(parts)


def build_executive_summary(report: dict, analytics: dict) -> dict:
    cmp_ = report.get("comparison") or {}
    study_chg = (cmp_.get("study_time") or {}).get("change_percent")
    grade_chg = (cmp_.get("grades") or {}).get("change_percent")
    att = analytics.get("attendance_rate") or 0
    planner = (cmp_.get("planner_adherence") or {}).get("current_value") or 0

    score = 0
    if study_chg and study_chg > 0:
        score += 1
    if grade_chg and grade_chg > 0:
        score += 1
    if att >= 55:
        score += 1
    if planner >= 60:
        score += 1
    if score >= 3:
        status = "أداء جيد — الطالب على المسار الصحيح"
    elif score >= 2:
        status = "أداء متوسط — بعض المجالات تحتاج دعماً"
    else:
        status = "يحتاج متابعة — نشاط أو نتائج دون المستوى المتوقع"

    improved: list[str] = []
    declined: list[str] = []
    attention: list[str] = []
    focus: list[str] = []

    if study_chg and study_chg >= 5:
        improved.append(f"وقت الدراسة (+{study_chg:.0f}%)")
    if grade_chg and grade_chg >= 5:
        improved.append(f"نتائج الاختبارات (+{grade_chg:.0f}%)")
    if planner >= 75:
        improved.append("الالتزام بالخطة")

    if study_chg and study_chg <= -5:
        declined.append(f"وقت الدراسة ({study_chg:.0f}%)")
    if grade_chg and grade_chg <= -5:
        declined.append(f"نتائج الاختبارات ({grade_chg:.0f}%)")
    if att < 45:
        attention.append("انتظام الحضور والدخول اليومي")
    if planner < 50:
        attention.append("الالتزام بالمخطط الدراسي")
    if not improved:
        improved.append("استقرار عام — فرصة لرفع النشاط")

    focus.append("جلسات دراسة قصيرة يومياً (20–30 دقيقة)")
    if grade_chg and grade_chg < 0:
        focus.append("مراجعة الاختبارات الأضعف")
    if planner < 60:
        focus.append("متابعة مهام المخطط الأسبوعي")

    return {
        "status": status,
        "improved": improved[:3],
        "declined": declined[:3] or ["لا تراجعات بارزة"],
        "attention": attention[:3] or ["لا مجالات حرجة"],
        "focus": focus[:3],
    }


def build_parent_insights(report: dict, analytics: dict) -> list[str]:
    insights: list[str] = []
    cmp_ = report.get("comparison") or {}
    study_chg = (cmp_.get("study_time") or {}).get("change_percent")

    if study_chg and study_chg >= 15:
        insights.append("تحسّنت عادات الدراسة بشكل ملحوظ.")
    elif study_chg and study_chg >= 5:
        insights.append("الطالب يصبح أكثر انتظاماً في الدراسة.")
    else:
        insights.append("عادات الدراسة تحتاج تشجيعاً مستمراً.")

    grade_chg = (cmp_.get("grades") or {}).get("change_percent")
    if grade_chg and grade_chg >= 5:
        insights.append("أداء الاختبارات في تحسّن.")
    elif (cmp_.get("grades") or {}).get("current_value", 0) >= 75:
        insights.append("نتائج الاختبارات مستقرة وجيدة.")
    else:
        insights.append("نتائج الاختبارات تحتاج متابعة.")

    att = analytics.get("attendance_rate") or 0
    if att >= 70:
        insights.append("انتظام الحضور ممتاز.")
    else:
        insights.append("الحضور يحتاج اهتمام ولي الأمر.")

    return insights[:4]


def build_comparison_rows(report: dict) -> list[dict]:
    cmp_ = report.get("comparison") or {}
    rows = []
    for key, label in [
        ("study_time", "وقت الدراسة"),
        ("grades", "متوسط الدرجات"),
        ("lesson_completion", "إكمال الدروس"),
        ("planner_adherence", "الالتزام بالخطة"),
    ]:
        m = cmp_.get(key) or {}
        chg = m.get("change_percent")
        if chg is None:
            chg_str = "—"
        elif chg >= 3:
            chg_str = f"▲ {chg:+.1f}%"
        elif chg <= -3:
            chg_str = f"▼ {chg:+.1f}%"
        else:
            chg_str = f"● {chg:+.1f}%"
        unit = m.get("unit") or ""
        rows.append(
            {
                "label": label,
                "current": f"{m.get('current_value', '—')} {unit}".strip(),
                "previous": f"{m.get('previous_value', '—')} {unit}".strip(),
                "change": chg_str,
            }
        )
    return rows


def build_kpi_strip(report: dict, analytics: dict) -> list[dict]:
    from app.services.parent_report_pdf_theme import DANGER, SUCCESS, TEXT_MUTED

    cmp_ = report.get("comparison") or {}

    def trend(chg: float | None) -> tuple[str, str]:
        if chg is None:
            return "—", TEXT_MUTED
        if chg >= 5:
            return f"▲ {chg:+.1f}%", SUCCESS
        if chg <= -5:
            return f"▼ {chg:+.1f}%", DANGER
        return f"● {chg:+.1f}%", TEXT_MUTED

    items = []
    for key, label, unit in [
        ("study_time", "وقت الدراسة", "ساعة"),
        ("grades", "متوسط الدرجات", "%"),
    ]:
        m = cmp_.get(key) or {}
        t, c = trend(m.get("change_percent"))
        val = m.get("current_value", "—")
        items.append({"label": label, "value": f"{val} {unit}".strip(), "trend": t, "trend_color": c})
    items.append(
        {
            "label": "إكمال الدورات",
            "value": f"{analytics.get('avg_course_completion', 0):.0f}%",
            "trend": "—",
            "trend_color": TEXT_MUTED,
        }
    )
    items.append(
        {
            "label": "معدل الحضور",
            "value": f"{analytics.get('attendance_rate', 0):.0f}%",
            "trend": "—",
            "trend_color": TEXT_MUTED,
        }
    )
    st = (cmp_.get("study_time") or {}).get("change_percent")
    t, c = trend(st)
    items.append({"label": "التحسن الأسبوعي", "value": f"{st:+.0f}%" if st is not None else "—", "trend": t, "trend_color": c})
    return items


async def build_pdf_analytics(
    db: AsyncSession,
    student_id: int,
    report: dict,
) -> dict:
    end = date.fromisoformat(report["end_date"])
    start = date.fromisoformat(report["start_date"])
    start_dt, end_dt = _range_dt(start, end)

    weekly_study = await _weekly_study_hours(db, student_id, end)
    weekly_grades = await _weekly_grade_trend(db, student_id, end)
    activity_breakdown = await _activity_breakdown(db, student_id, start_dt, end_dt)
    heatmap = await _attendance_heatmap(db, student_id, end)
    courses_raw = await list_student_grade_reports(db, student_id)
    course_progress = [
        {
            "title": c.get("course_title") or "",
            "subject": c.get("subject_name") or "",
            "completion": float(c.get("completion_percentage") or 0),
            "average_score": float(c.get("average_score") or 0),
            "attendance": float(c.get("attendance_percentage") or 0),
        }
        for c in courses_raw[:8]
    ]

    by_day = await _daily_study_minutes(db, student_id, start, end)
    weekend_min = sum(m for d, m in by_day.items() if d.weekday() in (4, 5))
    weekday_min = sum(m for d, m in by_day.items() if d.weekday() not in (4, 5))

    sessions = (report.get("attendance_history") or {}).get("login_sessions") or []
    attendance_rate = _attendance_rate(sessions, start, end)
    completions = [c["completion"] for c in course_progress if c.get("completion")]
    avg_course_completion = round(sum(completions) / len(completions), 1) if completions else 0.0

    lessons_weekly = (report.get("lesson_history") or {}).get("weekly") or []

    analytics = {
        "weekly_study_hours": weekly_study,
        "weekly_grades": weekly_grades,
        "activity_breakdown": activity_breakdown,
        "attendance_heatmap": heatmap,
        "course_progress": course_progress,
        "avg_course_completion": avg_course_completion,
        "attendance_rate": attendance_rate,
        "weekend_study_minutes": weekend_min,
        "weekday_study_minutes": weekday_min,
    }
    analytics["performance_timeline"] = build_performance_timeline(weekly_study, weekly_grades)
    analytics["weekly_performance"] = build_weekly_performance(
        weekly_study, weekly_grades, lessons_weekly, heatmap
    )
    analytics["risk_indicators"] = build_risk_indicators(report, analytics)
    analytics["achievements"] = build_achievements(report, analytics)
    analytics["narrative_summary"] = build_narrative_summary(report, analytics)
    analytics["executive_summary"] = build_executive_summary(report, analytics)
    analytics["parent_insights"] = build_parent_insights(report, analytics)
    analytics["comparison_rows"] = build_comparison_rows(report)
    analytics["kpi_strip"] = build_kpi_strip(report, analytics)
    analytics["insights"] = analytics["parent_insights"]
    return analytics
