"""Student smart planner API — wired to planner_intelligence_service."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_student_actor
from app.db.session import get_db
from app.models.planner import PlannerScheduleSlot, ScheduleSlotStatus
from app.models.user import User
from app.schemas.planner import (
    CompleteSessionRequest,
    PlannerChatRequest,
    PlannerChatResponse,
    PlannerStateOut,
)
from app.services.planner_chat_service import handle_planner_chat
from app.services.planner_intelligence_service import (
    generate_weekly_plan,
    get_enriched_planner_state,
)
from app.services.planner_streak_service import record_study_activity

router = APIRouter(prefix="/student/planner", tags=["Smart Planner"])


async def _state_out(db: AsyncSession, student_id: int, *, auto_generate: bool) -> PlannerStateOut:
    state = await get_enriched_planner_state(db, student_id, auto_generate=auto_generate)
    return PlannerStateOut.model_validate(state)


@router.get("", response_model=PlannerStateOut)
async def get_planner(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    state = await _state_out(db, student.id, auto_generate=True)
    await db.commit()
    return state


@router.get("/summary", response_model=PlannerStateOut)
async def get_planner_summary(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    state = await _state_out(db, student.id, auto_generate=False)
    return state


@router.post("/generate", response_model=PlannerStateOut)
async def generate_planner(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    await generate_weekly_plan(db, student.id)
    await db.commit()
    state = await get_enriched_planner_state(db, student.id, auto_generate=False)
    return PlannerStateOut.model_validate(state)


@router.post("/optimize", response_model=PlannerStateOut)
async def optimize_planner(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    await generate_weekly_plan(db, student.id)
    await db.commit()
    state = await get_enriched_planner_state(db, student.id, auto_generate=False)
    return PlannerStateOut.model_validate(state)


@router.post("/chat", response_model=PlannerChatResponse)
async def planner_chat(
    body: PlannerChatRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    result = await handle_planner_chat(db, student, body.message)
    state = await get_enriched_planner_state(db, student.id, auto_generate=False)
    return PlannerChatResponse.model_validate(
        {
            **state,
            "reply": result.get("reply", ""),
            "extracted_events": result.get("extracted_events", []),
        }
    )


@router.post("/sessions/complete", response_model=PlannerStateOut)
async def complete_planner_session(
    body: CompleteSessionRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    result = await db.execute(
        select(PlannerScheduleSlot).where(
            PlannerScheduleSlot.id == body.slot_id,
            PlannerScheduleSlot.student_id == student.id,
        )
    )
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="المهمة غير موجودة")
    slot.status = ScheduleSlotStatus.completed
    await record_study_activity(db, student.id)
    await db.commit()
    state = await get_enriched_planner_state(db, student.id, auto_generate=False)
    return PlannerStateOut.model_validate(state)
