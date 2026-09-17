"""AI speaking coach API — structured turn evaluation with low-latency two-phase output."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends

from app.core.deps import require_student_actor
from app.models.user import User
from app.schemas.speaking_coach import CoachExplanationOut, CoachTurnIn, CoachTurnOut
from app.services.speaking_coach_service import (
    coach_turn,
    generate_explanation_task,
    get_explanation,
    reset_session,
)

router = APIRouter(prefix="/speaking/coach", tags=["Speaking Coach"])


@router.post("/turn", response_model=CoachTurnOut)
async def speaking_coach_turn(
    body: CoachTurnIn,
    background_tasks: BackgroundTasks,
    _student: User = Depends(require_student_actor()),
):
    result = await coach_turn(
        session_id=body.session_id,
        transcript=body.transcript,
        cefr_level=body.cefr_level,
        defer_explanation=body.defer_explanation,
    )
    if result.get("explanation_pending"):
        background_tasks.add_task(
            generate_explanation_task,
            turn_id=result["turn_id"],
            original=result["user_sentence_evaluated"],
            corrected=result["corrected_sentence"],
            cefr_level=body.cefr_level,
        )
    return CoachTurnOut(**result)


@router.get("/turn/{turn_id}/explanation", response_model=CoachExplanationOut)
async def speaking_coach_explanation(
    turn_id: str,
    _student: User = Depends(require_student_actor()),
):
    text = get_explanation(turn_id)
    return CoachExplanationOut(turn_id=turn_id, explanation=text, ready=text is not None)


@router.delete("/session/{session_id}")
async def speaking_coach_reset(
    session_id: str,
    _student: User = Depends(require_student_actor()),
):
    await reset_session(session_id)
    return {"ok": True}
