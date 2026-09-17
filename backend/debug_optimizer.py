import asyncio
from datetime import datetime, timedelta, timezone
from app.db.session import get_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.planner import PlannerProfile, PlannerLifeEvent
from app.services.schedule_optimizer import _is_blocked, _slot_datetime, PERIOD_HOURS

async def debug():
    engine = get_async_engine()
    async with AsyncSession(engine) as db:
        pr = (await db.execute(select(PlannerProfile).where(PlannerProfile.student_id==2))).scalar_one()
        evs = list((await db.execute(select(PlannerLifeEvent).where(PlannerLifeEvent.student_id==2))).scalars().all())

        period = pr.preferred_period or 'evening'
        start_h, end_h = PERIOD_HOURS.get(period, PERIOD_HOURS['evening'])
        print(f"Period={period} Hours={start_h}-{end_h} MaxMin={pr.max_daily_minutes}")

        now = datetime.now(timezone.utc)
        print(f"Now UTC: {now}")

        session_minutes = 40
        for day_off in range(4):
            day = (now + timedelta(days=day_off)).replace(hour=0, minute=0, second=0, microsecond=0)
            fmt = day.strftime("%A %d-%m")
            print(f"\nDay {day_off}: {fmt}")
            daily_minutes = 0
            for h in range(start_h, end_h):
                slot_dt = _slot_datetime(day, h)
                past = slot_dt <= now
                blocked = _is_blocked(slot_dt, session_minutes, evs, pr)
                can_add = not past and not blocked and (daily_minutes + session_minutes <= pr.max_daily_minutes)
                print(f"  {h}:00 past={past} blocked={blocked} can_add={can_add}")
                if can_add:
                    daily_minutes += session_minutes + 15

asyncio.run(debug())
