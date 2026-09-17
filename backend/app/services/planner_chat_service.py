"""Orchestrates chat-to-planner flow: extract → update → optimize → explain."""

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planner import LifeEventType, PlannerChatMessage, PlannerLifeEvent, PlannerScheduleSlot
from app.models.user import User
from app.services.activity_service import log_planner_generated
from app.services.event_extraction_service import extract_from_message, try_llm_augment
from app.services.planner_memory_service import get_or_create_profile, profile_to_dict, update_profile_from_extraction
from app.services.schedule_optimizer import optimize_schedule


async def persist_life_events(db: AsyncSession, student_id: int, events: list[dict]) -> list[PlannerLifeEvent]:
    saved = []
    for ev in events:
        event_date = None
        if ev.get("event_date"):
            try:
                event_date = datetime.fromisoformat(ev["event_date"].replace("Z", "+00:00"))
            except Exception:
                event_date = None
        ev_type_raw = ev.get("event_type", "other")
        try:
            ev_type = LifeEventType(ev_type_raw)
        except ValueError:
            ev_type = LifeEventType.other
        row = PlannerLifeEvent(
            student_id=student_id,
            title=ev.get("title", "حدث"),
            event_type=ev_type,
            day_of_week=ev.get("day_of_week"),
            event_date=event_date,
            start_time=ev.get("start_time"),
            duration_minutes=ev.get("duration_minutes", 60),
            is_blocking=ev.get("is_blocking", True),
            subject=ev.get("subject"),
            metadata_json=json.dumps(ev, ensure_ascii=False),
        )
        db.add(row)
        saved.append(row)
    await db.flush()
    return saved


def _build_reply(extracted: dict, slot_count: int, reasoning: list[str]) -> str:
    parts = ["تم تحديث جدولك الدراسي بناءً على ما شاركته."]

    if extracted.get("life_events"):
        parts.append(f"• أضفت {len(extracted['life_events'])} حدث/موعد إلى تقويمك.")
    if extracted.get("weak_subjects"):
        parts.append(f"• سأركز على: {', '.join(extracted['weak_subjects'])}.")
    if extracted.get("profile_updates", {}).get("preferred_period"):
        period = extracted["profile_updates"]["preferred_period"]
        label = {"morning": "الصباح", "evening": "المساء", "night": "الليل"}.get(period, period)
        parts.append(f"• ضبطت وقت الدراسة المفضل: {label}.")

    parts.append(f"• جدولت {slot_count} جلسة دراسة للأسبوع القادم.")

    if reasoning:
        parts.append("\n**لماذا هذا الترتيب؟**")
        for r in reasoning[:4]:
            parts.append(f"— {r}")

    parts.append("\nيمكنك إخباري بأي تغيير جديد وسأعيد الترتيب تلقائياً.")
    return "\n".join(parts)


async def handle_planner_chat(
    db: AsyncSession,
    student: User,
    message: str,
) -> dict:
    db.add(PlannerChatMessage(student_id=student.id, role="user", content=message))
    await db.flush()

    extracted = extract_from_message(message)
    extracted = await try_llm_augment(message, extracted)

    profile = await get_or_create_profile(db, student.id)
    await update_profile_from_extraction(
        db,
        profile,
        {
            **extracted.get("profile_updates", {}),
            "weak_subjects": extracted.get("weak_subjects", []),
            "notes": extracted.get("notes", []),
        },
    )

    if extracted.get("life_events"):
        await persist_life_events(db, student.id, extracted["life_events"])

    slots, reasoning = await optimize_schedule(db, student.id, profile)

    reply = _build_reply(extracted, len(slots), reasoning)
    db.add(
        PlannerChatMessage(
            student_id=student.id,
            role="ai",
            content=reply,
            metadata_json=json.dumps({"reasoning": reasoning}, ensure_ascii=False),
        )
    )

    if slots:
        await log_planner_generated(
            db,
            student_id=student.id,
            student_name=student.name.split()[0] if student.name else "الطالب",
            slot_count=len(slots),
        )

    await db.commit()

    schedule_out = [_slot_out(s) for s in slots]
    return {
        "reply": reply,
        "extracted_events": extracted.get("life_events", []),
        "schedule": schedule_out,
        "reasoning": reasoning,
        "profile": profile_to_dict(profile),
    }


async def get_planner_state(db: AsyncSession, student_id: int) -> dict:
    profile = await get_or_create_profile(db, student_id)

    ev_result = await db.execute(
        select(PlannerLifeEvent)
        .where(PlannerLifeEvent.student_id == student_id)
        .order_by(PlannerLifeEvent.event_date.asc().nullslast(), PlannerLifeEvent.created_at.desc())
        .limit(80)
    )
    life_events = ev_result.scalars().all()

    slot_result = await db.execute(
        select(PlannerScheduleSlot)
        .where(PlannerScheduleSlot.student_id == student_id)
        .order_by(PlannerScheduleSlot.scheduled_at)
        .limit(50)
    )
    slots = slot_result.scalars().all()

    chat_result = await db.execute(
        select(PlannerChatMessage)
        .where(PlannerChatMessage.student_id == student_id)
        .order_by(PlannerChatMessage.created_at)
        .limit(30)
    )
    messages = chat_result.scalars().all()

    reasoning = []
    for s in slots[:5]:
        if s.reasoning:
            reasoning.append(f"{s.subject}: {s.reasoning}")

    insights = []
    weak = profile_to_dict(profile).get("weak_subjects", [])
    if weak:
        insights.append(f"ركز هذا الأسبوع على: {', '.join(weak)}")
    upcoming = [s for s in slots if s.scheduled_at > datetime.now(timezone.utc)][:3]
    if upcoming:
        insights.append(f"الجلسة القادمة: {upcoming[0].subject}")

    return {
        "profile": profile_to_dict(profile),
        "life_events": [_event_out(e) for e in life_events],
        "schedule": [_slot_out(s) for s in slots],
        "chat_history": [
            {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at}
            for m in messages
        ],
        "reasoning": reasoning,
        "insights": insights,
    }


def _slot_out(s: PlannerScheduleSlot) -> dict:
    return {
        "id": s.id,
        "subject": s.subject,
        "scheduled_at": s.scheduled_at,
        "duration_minutes": s.duration_minutes,
        "priority": s.priority,
        "status": s.status.value if hasattr(s.status, "value") else s.status,
        "reasoning": s.reasoning,
    }


def _event_out(e: PlannerLifeEvent) -> dict:
    return {
        "id": e.id,
        "title": e.title,
        "event_type": e.event_type.value if hasattr(e.event_type, "value") else e.event_type,
        "day_of_week": e.day_of_week,
        "event_date": e.event_date,
        "start_time": e.start_time,
        "duration_minutes": e.duration_minutes,
        "is_blocking": e.is_blocking,
        "subject": e.subject,
    }
