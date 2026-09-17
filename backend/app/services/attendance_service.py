"""Attendance tracking: persistence, demo generation, and aggregated summaries."""

import logging
import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceStatus, StudentAttendanceRecord

logger = logging.getLogger(__name__)

AR_WEEKDAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]

# Believable demo patterns (weekday index: Mon=0 .. Sun=6)
_DEMO_PATTERNS = {
    6: (AttendanceStatus.present, (90, 130)),   # Sunday
    0: (AttendanceStatus.absent, (0, 0)),
    1: (AttendanceStatus.partial, (35, 55)),
    2: (AttendanceStatus.present, (100, 140)),
    3: (AttendanceStatus.present, (80, 110)),
    4: (AttendanceStatus.absent, (0, 0)),       # Friday / match day
    5: (AttendanceStatus.partial, (40, 70)),
}


def _day_label(d: date) -> str:
    return AR_WEEKDAYS[d.weekday()]


def _status_score(status: AttendanceStatus, minutes: int) -> int:
    if status == AttendanceStatus.absent:
        return 0
    if status == AttendanceStatus.partial:
        return min(100, 40 + minutes // 2)
    return min(100, 55 + minutes // 2)


async def has_attendance_data(db: AsyncSession, student_id: int) -> bool:
    result = await db.execute(
        select(StudentAttendanceRecord.id)
        .where(StudentAttendanceRecord.student_id == student_id)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def seed_demo_attendance(
    db: AsyncSession,
    student_id: int,
    *,
    days: int = 28,
) -> int:
    """DEPRECATED — not called in production. Attendance is recorded from real student activity only."""
    if await has_attendance_data(db, student_id):
        return 0

    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)
    rng = random.Random(student_id * 9973)
    created = 0

    for offset in range(days):
        d = start + timedelta(days=offset)
        if d > today:
            continue
        wd = d.weekday()
        base_status, (lo, hi) = _DEMO_PATTERNS.get(wd, (AttendanceStatus.partial, (30, 60)))

        roll = rng.random()
        if roll < 0.12 and base_status == AttendanceStatus.present:
            status = AttendanceStatus.partial
            minutes = rng.randint(25, 50)
        elif roll < 0.08 and base_status != AttendanceStatus.absent:
            status = AttendanceStatus.absent
            minutes = 0
        else:
            status = base_status
            minutes = 0 if status == AttendanceStatus.absent else rng.randint(lo, hi)

        notes = None
        if status == AttendanceStatus.absent and wd == 4:
            notes = "مناسبة عائلية / مباراة"
        elif status == AttendanceStatus.partial:
            notes = "جلسة قصيرة — انشغال"
        elif status == AttendanceStatus.present and minutes >= 100:
            notes = "جلسة مركزة"

        db.add(
            StudentAttendanceRecord(
                student_id=student_id,
                date=d,
                status=status,
                study_minutes=minutes,
                consistency_score=_status_score(status, minutes),
                notes=notes,
            )
        )
        created += 1

    await db.flush()
    logger.info("Seeded %s attendance records for student %s", created, student_id)
    return created


async def list_records(
    db: AsyncSession,
    student_id: int,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[StudentAttendanceRecord]:
    q = (
        select(StudentAttendanceRecord)
        .where(StudentAttendanceRecord.student_id == student_id)
        .order_by(StudentAttendanceRecord.date.desc())
    )
    if from_date:
        q = q.where(StudentAttendanceRecord.date >= from_date)
    if to_date:
        q = q.where(StudentAttendanceRecord.date <= to_date)
    result = await db.execute(q)
    return list(result.scalars().all())


def record_to_out(rec: StudentAttendanceRecord) -> dict:
    return {
        "id": rec.id,
        "student_id": rec.student_id,
        "date": rec.date,
        "status": rec.status.value if hasattr(rec.status, "value") else rec.status,
        "study_minutes": rec.study_minutes,
        "consistency_score": rec.consistency_score,
        "notes": rec.notes,
        "day_label": _day_label(rec.date),
        "created_at": rec.created_at,
    }


def _compute_streak(sorted_records: list[StudentAttendanceRecord], *, today: date) -> int:
    """Consecutive present/partial days ending at today or yesterday."""
    by_date = {r.date: r for r in sorted_records}
    streak = 0
    cursor = today
    for _ in range(60):
        rec = by_date.get(cursor)
        if not rec or rec.status == AttendanceStatus.absent:
            break
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _week_consistency(records: list[StudentAttendanceRecord]) -> int:
    if not records:
        return 0
    scores = [r.consistency_score for r in records]
    return round(sum(scores) / len(scores))


async def build_attendance_summary(
    db: AsyncSession,
    student_id: int,
    child_name: str,
) -> dict:
    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1)
    range_start = today - timedelta(days=27)

    all_records = await list_records(db, student_id, from_date=range_start, to_date=today)
    by_date = {r.date: r for r in all_records}

    # Current week (last 7 days)
    week_start = today - timedelta(days=6)
    week_records = [by_date.get(week_start + timedelta(days=i)) for i in range(7)]
    week_records = [r for r in week_records if r]

    present_week = sum(1 for r in week_records if r.status == AttendanceStatus.present)
    partial_week = sum(1 for r in week_records if r.status == AttendanceStatus.partial)
    absent_week = sum(1 for r in week_records if r.status == AttendanceStatus.absent)
    weekly_consistency = _week_consistency(week_records)
    total_minutes_week = sum(r.study_minutes for r in week_records)

    # Monthly buckets (4 weeks in current month view)
    monthly_overview = []
    for w in range(4):
        w_start = month_start + timedelta(days=w * 7)
        w_end = min(w_start + timedelta(days=6), today)
        if w_start > today:
            break
        w_recs = [by_date.get(w_start + timedelta(days=i)) for i in range(7)]
        w_recs = [r for r in w_recs if r and r.date <= today]
        if not w_recs:
            continue
        p = sum(1 for r in w_recs if r.status == AttendanceStatus.present)
        a = sum(1 for r in w_recs if r.status == AttendanceStatus.absent)
        pt = sum(1 for r in w_recs if r.status == AttendanceStatus.partial)
        monthly_overview.append(
            {
                "week_index": w + 1,
                "label": f"الأسبوع {w + 1}",
                "consistency": _week_consistency(w_recs),
                "present": p,
                "absent": a,
                "partial": pt,
            }
        )

    # Last 4 weeks consistency bars
    consistency_bars = []
    for w in range(4):
        bar_end = today - timedelta(days=w * 7)
        bar_start = bar_end - timedelta(days=6)
        bar_recs = [
            by_date.get(bar_start + timedelta(days=i))
            for i in range(7)
            if bar_start + timedelta(days=i) <= today
        ]
        bar_recs = [r for r in bar_recs if r]
        if bar_recs:
            consistency_bars.insert(
                0,
                {
                    "week_label": f"{bar_start.day}/{bar_start.month}",
                    "consistency": _week_consistency(bar_recs),
                    "present_days": sum(
                        1 for r in bar_recs if r.status in (AttendanceStatus.present, AttendanceStatus.partial)
                    ),
                    "total_days": len(bar_recs),
                },
            )

    weekly_calendar = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        rec = by_date.get(d)
        if rec:
            st = rec.status.value if hasattr(rec.status, "value") else rec.status
            weekly_calendar.append(
                {
                    "date": d.isoformat(),
                    "day_label": _day_label(d),
                    "status": st,
                    "study_minutes": rec.study_minutes,
                    "consistency_score": rec.consistency_score,
                    "active": st != "absent",
                }
            )
        else:
            weekly_calendar.append(
                {
                    "date": d.isoformat(),
                    "day_label": _day_label(d),
                    "status": "absent",
                    "study_minutes": 0,
                    "consistency_score": 0,
                    "active": False,
                }
            )

    streak = _compute_streak(all_records, today=today)
    inactive_days = sum(1 for r in all_records if r.status == AttendanceStatus.absent)
    active_days = len(all_records) - inactive_days
    attendance_pct = round((active_days / len(all_records)) * 100) if all_records else 0

    alerts = []
    if absent_week > 0:
        alerts.append(
            {"type": "warning", "text": f"فات {child_name} {absent_week} يوم/أيام دراسة هذا الأسبوع"}
        )
    if streak >= 3:
        alerts.append({"type": "success", "text": f"{child_name} درس {streak} أيام متتالية"})
    yesterday = today - timedelta(days=1)
    y_rec = by_date.get(yesterday)
    if y_rec and y_rec.status == AttendanceStatus.absent:
        alerts.append({"type": "info", "text": f"{child_name} لم يدرس أمس"})
    if weekly_consistency < 50:
        alerts.append({"type": "warning", "text": "التزام الدراسة منخفض هذا الأسبوع — يُنصح بالمتابعة"})

    ai_insights = _build_ai_insights(child_name, week_records, weekly_consistency, streak, attendance_pct)

    recent_records = [record_to_out(r) for r in sorted(all_records, key=lambda x: x.date, reverse=True)[:14]]

    return {
        "attendance_percentage": attendance_pct,
        "weekly_consistency": weekly_consistency,
        "streak_days": streak,
        "inactive_days": inactive_days,
        "completed_sessions": present_week,
        "missed_sessions": absent_week,
        "partial_days": partial_week,
        "total_study_minutes_week": total_minutes_week,
        "weekly_calendar": weekly_calendar,
        "monthly_overview": monthly_overview,
        "consistency_bars": consistency_bars,
        "alerts": alerts,
        "ai_insights": ai_insights,
        "recent_records": recent_records,
        # Legacy fields for existing parent dashboard widgets
        "daily": [{"date": c["date"], "label": c["day_label"], "active": c["active"]} for c in weekly_calendar],
    }


def _build_ai_insights(
    child_name: str,
    week_records: list[StudentAttendanceRecord],
    weekly_consistency: int,
    streak: int,
    attendance_pct: int,
) -> list[str]:
    insights = []
    if weekly_consistency >= 75:
        insights.append(f"التزام {child_name} بالدراسة جيد هذا الأسبوع ({weekly_consistency}%)")
    elif weekly_consistency < 55:
        insights.append(f"يبدو أن نشاط دراسة {child_name} انخفض هذا الأسبوع")
    if streak >= 4:
        insights.append(f"سلسلة إيجابية: {streak} أيام دراسة متتالية")
    partials = [r for r in week_records if r and r.status == AttendanceStatus.partial]
    if len(partials) >= 2:
        insights.append("عدة جلسات جزئية — قد يحتاج جدولاً أوضح")
    if attendance_pct >= 80:
        insights.append(f"نسبة الحضور الدراسي الشهرية ممتازة ({attendance_pct}%)")
    return insights[:4]
