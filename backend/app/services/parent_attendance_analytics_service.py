"""Parent attendance analytics — aggregated from real activity tracking data."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import StudentProfile
from app.models.student_activity_tracking import StudentActivitySession, StudentEngagementEvent

AR_WEEKDAYS = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _day_label(d: date) -> str:
    return AR_WEEKDAYS[(d.weekday() + 1) % 7]


def _week_start_sunday(d: date, *, offset: int = 0) -> date:
    days_since_sunday = (d.weekday() + 1) % 7
    start = d - timedelta(days=days_since_sunday)
    return start - timedelta(days=7 * offset)


def _month_start(d: date, *, offset: int = 0) -> date:
    year, month = d.year, d.month - offset
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def _month_end(month_start: date) -> date:
    if month_start.month == 12:
        nxt = date(month_start.year + 1, 1, 1)
    else:
        nxt = date(month_start.year, month_start.month + 1, 1)
    return nxt - timedelta(days=1)


def _range_dt(start: date, end: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    return start_dt, end_dt


def _pct_change(current: int, previous: int) -> float | None:
    if previous <= 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def _enum_or_str(value) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def _trend(current: int, previous: int) -> str:
    delta = _pct_change(current, previous)
    if delta is None:
        return "flat"
    if delta >= 5:
        return "up"
    if delta <= -5:
        return "down"
    return "flat"


async def _sum_study_seconds(
    db: AsyncSession,
    student_id: int,
    start_dt: datetime,
    end_dt: datetime,
) -> int:
    value = (
        await db.execute(
            select(func.coalesce(func.sum(StudentEngagementEvent.counted_seconds), 0)).where(
                StudentEngagementEvent.student_id == student_id,
                StudentEngagementEvent.occurred_at >= start_dt,
                StudentEngagementEvent.occurred_at < end_dt,
            )
        )
    ).scalar_one()
    return int(value or 0)


async def _daily_study_minutes(
    db: AsyncSession,
    student_id: int,
    start: date,
    end: date,
) -> dict[date, int]:
    start_dt, end_dt = _range_dt(start, end)
    result = await db.execute(
        select(
            func.date(StudentEngagementEvent.occurred_at).label("day"),
            func.coalesce(func.sum(StudentEngagementEvent.counted_seconds), 0).label("seconds"),
        )
        .where(
            StudentEngagementEvent.student_id == student_id,
            StudentEngagementEvent.occurred_at >= start_dt,
            StudentEngagementEvent.occurred_at < end_dt,
        )
        .group_by(func.date(StudentEngagementEvent.occurred_at))
    )
    out: dict[date, int] = {}
    for row in result.all():
        day = row.day
        if isinstance(day, str):
            day = date.fromisoformat(day)
        out[day] = int(row.seconds or 0) // 60
    return out


def _daily_breakdown(start: date, end: date, by_day: dict[date, int]) -> list[dict]:
    rows: list[dict] = []
    cursor = start
    while cursor <= end:
        minutes = by_day.get(cursor, 0)
        rows.append(
            {
                "date": cursor.isoformat(),
                "day_label": _day_label(cursor),
                "study_minutes": minutes,
            }
        )
        cursor += timedelta(days=1)
    return rows


def _weekly_analytics(days: list[dict], *, period_label: str, comparison_percent: float | None) -> dict:
    active_days = [d for d in days if d["study_minutes"] > 0]
    total = sum(d["study_minutes"] for d in days)
    avg = round(total / len(days), 1) if days else 0.0

    most = max(days, key=lambda d: d["study_minutes"]) if days else None
    least_candidates = active_days or days
    least = min(least_candidates, key=lambda d: d["study_minutes"]) if least_candidates else None

    return {
        "period_label": period_label,
        "total_minutes": total,
        "daily_average_minutes": avg,
        "most_active_day": most,
        "least_active_day": least,
        "comparison_percent": comparison_percent,
        "active_days_count": len(active_days),
    }


def _month_weekly_buckets(month_start: date, month_end: date, by_day: dict[date, int]) -> list[dict]:
    buckets: list[dict] = []
    cursor = _week_start_sunday(month_start)
    week_idx = 1
    while cursor <= month_end:
        week_end = min(cursor + timedelta(days=6), month_end)
        if week_end < month_start:
            cursor += timedelta(days=7)
            continue
        effective_start = max(cursor, month_start)
        total = 0
        d = effective_start
        while d <= week_end:
            total += by_day.get(d, 0)
            d += timedelta(days=1)
        buckets.append({"week_index": week_idx, "study_minutes": total})
        week_idx += 1
        cursor += timedelta(days=7)
    return buckets


async def _login_history(
    db: AsyncSession,
    student_id: int,
    *,
    start_dt: datetime,
    end_dt: datetime,
    limit: int,
) -> list[dict]:
    result = await db.execute(
        select(StudentActivitySession)
        .where(
            StudentActivitySession.student_id == student_id,
            StudentActivitySession.login_at >= start_dt,
            StudentActivitySession.login_at < end_dt,
        )
        .order_by(StudentActivitySession.login_at.desc())
        .limit(limit)
    )
    rows: list[dict] = []
    for session in result.scalars().all():
        login_at = session.login_at
        logout_at = session.logout_at
        rows.append(
            {
                "id": session.id,
                "date": login_at.date().isoformat() if login_at else None,
                "day_label": _day_label(login_at.date()) if login_at else None,
                "login_at": login_at.isoformat() if login_at else None,
                "logout_at": logout_at.isoformat() if logout_at else None,
                "logout_reason": _enum_or_str(session.logout_reason),
                "active_minutes": int(session.active_minutes or 0),
                "is_open": logout_at is None,
            }
        )
    return rows


async def build_parent_attendance_analytics(
    db: AsyncSession,
    student_id: int,
    *,
    week_offset: int = 0,
    month_offset: int = 0,
    session_limit: int = 30,
) -> dict:
    today = _utcnow().date()
    profile = (
        await db.execute(select(StudentProfile).where(StudentProfile.user_id == student_id))
    ).scalar_one_or_none()

    # Overview: today / this calendar week (Sun-Sat) / this calendar month
    today_start, today_end_dt = _range_dt(today, today)
    today_seconds = await _sum_study_seconds(db, student_id, today_start, today_end_dt)

    this_week_start = _week_start_sunday(today, offset=0)
    this_week_end = this_week_start + timedelta(days=6)
    tw_start_dt, tw_end_dt = _range_dt(this_week_start, this_week_end)
    this_week_seconds = await _sum_study_seconds(db, student_id, tw_start_dt, tw_end_dt)

    this_month_start = _month_start(today, offset=0)
    this_month_end = min(_month_end(this_month_start), today)
    tm_start_dt, tm_end_dt = _range_dt(this_month_start, this_month_end)
    this_month_seconds = await _sum_study_seconds(db, student_id, tm_start_dt, tm_end_dt)

    prev_week_start = _week_start_sunday(today, offset=1)
    prev_week_end = prev_week_start + timedelta(days=6)
    pw_start_dt, pw_end_dt = _range_dt(prev_week_start, prev_week_end)
    prev_week_seconds = await _sum_study_seconds(db, student_id, pw_start_dt, pw_end_dt)

    prev_month_start = _month_start(today, offset=1)
    prev_month_end = _month_end(prev_month_start)
    pm_start_dt, pm_end_dt = _range_dt(prev_month_start, prev_month_end)
    prev_month_seconds = await _sum_study_seconds(db, student_id, pm_start_dt, pm_end_dt)

    week_comparison = _pct_change(this_week_seconds, prev_week_seconds)
    month_comparison = _pct_change(this_month_seconds, prev_month_seconds)

    # Selected week view (historical navigation)
    selected_week_start = _week_start_sunday(today, offset=week_offset)
    selected_week_end = selected_week_start + timedelta(days=6)
    if selected_week_end > today and week_offset == 0:
        selected_week_end = today

    compare_week_start = _week_start_sunday(today, offset=week_offset + 1)
    compare_week_end = compare_week_start + timedelta(days=6)

    sw_by_day = await _daily_study_minutes(db, student_id, selected_week_start, selected_week_end)
    cw_by_day = await _daily_study_minutes(db, student_id, compare_week_start, compare_week_end)
    selected_week_days = _daily_breakdown(selected_week_start, selected_week_end, sw_by_day)
    selected_week_total = sum(d["study_minutes"] for d in selected_week_days)
    compare_week_total = sum(cw_by_day.values())
    selected_week_comparison = _pct_change(selected_week_total, compare_week_total)

    week_labels = {
        0: "هذا الأسبوع",
        1: "الأسبوع السابق",
    }
    week_period_label = week_labels.get(week_offset, f"أسبوع {selected_week_start.isoformat()}")

    # Selected month view
    selected_month_start = _month_start(today, offset=month_offset)
    selected_month_end = min(_month_end(selected_month_start), today) if month_offset == 0 else _month_end(selected_month_start)
    sm_by_day = await _daily_study_minutes(db, student_id, selected_month_start, selected_month_end)
    selected_month_total = sum(sm_by_day.values())

    compare_month_start = _month_start(today, offset=month_offset + 1)
    compare_month_end = _month_end(compare_month_start)
    cm_by_day = await _daily_study_minutes(db, student_id, compare_month_start, compare_month_end)
    compare_month_total = sum(cm_by_day.values())
    selected_month_comparison = _pct_change(selected_month_total, compare_month_total)

    month_labels = {
        0: "هذا الشهر",
        1: "الشهر السابق",
    }
    month_period_label = month_labels.get(month_offset, f"{selected_month_start.strftime('%Y-%m')}")

    monthly_weeks = _month_weekly_buckets(selected_month_start, selected_month_end, sm_by_day)
    weekly_avg_in_month = (
        round(selected_month_total / len(monthly_weeks), 1) if monthly_weeks else 0.0
    )

    # Login history for visible period (week or month based on what's selected - include both ranges union)
    history_start = min(selected_week_start, selected_month_start)
    history_end = max(selected_week_end, selected_month_end)
    hist_start_dt, hist_end_dt = _range_dt(history_start, history_end)
    login_history = await _login_history(
        db,
        student_id,
        start_dt=hist_start_dt,
        end_dt=hist_end_dt,
        limit=session_limit,
    )

    # Rolling study-time averages for parent portal
    last_30_start = today - timedelta(days=29)
    last_30_start_dt, last_30_end_dt = _range_dt(last_30_start, today)
    last_30_seconds = await _sum_study_seconds(db, student_id, last_30_start_dt, last_30_end_dt)

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

    study_time_averages = {
        "daily_hours": round((last_30_seconds / 30) / 3600, 1),
        "weekly_hours": round(sum(week_totals_hours) / len(week_totals_hours), 1) if week_totals_hours else 0,
        "monthly_hours": round(this_month_seconds / 3600, 1),
        "daily_trend_percent": _pct_change(last_7_seconds // 7, prev_7_seconds // 7),
        "weekly_trend_percent": week_comparison,
        "monthly_trend_percent": month_comparison,
    }

    return {
        "overview": {
            "today_minutes": today_seconds // 60,
            "week_minutes": this_week_seconds // 60,
            "month_minutes": this_month_seconds // 60,
            "last_activity_at": (
                profile.last_activity_at.isoformat()
                if profile and profile.last_activity_at
                else None
            ),
            "week_comparison_percent": week_comparison,
            "month_comparison_percent": month_comparison,
            "averages": study_time_averages,
        },
        "week_offset": week_offset,
        "month_offset": month_offset,
        "daily_breakdown": selected_week_days,
        "weekly_analytics": _weekly_analytics(
            selected_week_days,
            period_label=week_period_label,
            comparison_percent=selected_week_comparison,
        ),
        "monthly_analytics": {
            "period_label": month_period_label,
            "total_minutes": selected_month_total,
            "weekly_average_minutes": weekly_avg_in_month,
            "comparison_percent": selected_month_comparison,
            "trend": _trend(selected_month_total, compare_month_total),
            "weeks": monthly_weeks,
            "daily_breakdown": _daily_breakdown(selected_month_start, selected_month_end, sm_by_day),
        },
        "login_history": login_history,
        "data_source": {
            "sessions_table": "student_activity_sessions",
            "events_table": "student_engagement_events",
            "last_activity_field": "student_profiles.last_activity_at",
        },
    }
