"""Speaking S9 adaptive learning journey API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.language_speaking_journey import (
    SpeakingActivityCompleteIn,
    SpeakingAlexContextOut,
    SpeakingJourneyMissionOut,
    SpeakingJourneyOut,
    SpeakingJourneyReadModelOut,
    SpeakingJourneyStepOut,
    SpeakingSessionActivityOut,
    SpeakingSessionOutcomeOut,
    SpeakingSessionStartIn,
    SpeakingSessionStartOut,
    SpeakingSessionTurnIn,
)
from app.services.language_access_service import require_language_learning_ready
from app.services.language_speaking_journey.api_service import (
    complete_speaking_activity,
    finalize_speaking_session,
    get_speaking_journey,
    prepare_speaking_session_for_live,
    record_speaking_session_turn,
    start_speaking_session,
)
from app.services.language_speaking_progression.runtime import run_speaking_progression_engines

router = APIRouter(prefix="/student/languages", tags=["Speaking Journey S9"])


def _journey_out(raw: dict) -> SpeakingJourneyOut:
    steps = [SpeakingJourneyStepOut.model_validate(s) for s in raw.get("steps") or []]
    missions = [SpeakingJourneyMissionOut.model_validate(m) for m in raw.get("today_missions") or []]
    read_raw = raw.get("read_model")
    read_model = SpeakingJourneyReadModelOut.model_validate(read_raw) if isinstance(read_raw, dict) else None
    return SpeakingJourneyOut(
        version=str(raw.get("version", "9.0.0")),
        current_focus_label=str(raw.get("current_focus_label", "")),
        current_focus_reason=str(raw.get("current_focus_reason", "")),
        session_goal=str(raw.get("session_goal", "")),
        official_level=str(raw.get("official_level", "")),
        plan_summary=str(raw.get("plan_summary", "")),
        today_session_id=str(raw.get("today_session_id", "")),
        today_session_phase=str(raw.get("today_session_phase", "")),
        current_activity_title=str(raw.get("current_activity_title", "")),
        steps=steps,
        next_recommendation=str(raw.get("next_recommendation", "")),
        has_active_session=bool(raw.get("has_active_session")),
        practice_with_alex_available=bool(raw.get("practice_with_alex_available", True)),
        today_missions=missions,
        current_attempt_number=int(raw.get("current_attempt_number", 0) or 0),
        is_retry=bool(raw.get("is_retry", False)),
        completed_task_attempt_count=int(raw.get("completed_task_attempt_count", 0) or 0),
        current_activity_id=str(raw.get("current_activity_id", "")),
        current_activity_instructions=str(raw.get("current_activity_instructions", "")),
        live_execution_ready=bool(raw.get("live_execution_ready", False)),
        lesson_title=str(raw.get("lesson_title") or raw.get("session_goal", "")),
        current_activity_kind=str(raw.get("current_activity_kind", "")),
        activities_total=int(raw.get("activities_total", 0) or 0),
        activities_completed=int(raw.get("activities_completed", 0) or 0),
        activities_remaining=int(raw.get("activities_remaining", 0) or 0),
        read_model=read_model,
    )


@router.get("/speaking/journey", response_model=SpeakingJourneyOut)
async def speaking_journey(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    # Ensure readiness projection exists for Journey Home (API orchestration — not journey→progression).
    from app.services.language_progression_service import ensure_progression_row

    row = await ensure_progression_row(db, student_id=student.id, language_id=1)
    if row is not None:
        payload = dict(row.promotion_readiness_json or {})
        speaking_promo = payload.get("speaking_promotion")
        has_proj = isinstance(speaking_promo, dict) and isinstance(
            speaking_promo.get("student_projection"), dict
        )
        if not has_proj:
            await run_speaking_progression_engines(db, student_id=student.id, language_id=1)

    bundle = await get_speaking_journey(db, student_id=student.id, language_id=1)
    await db.commit()
    return _journey_out(bundle.to_student_dict())


@router.post("/speaking/journey/session/start", response_model=SpeakingSessionStartOut)
async def speaking_session_start(
    body: SpeakingSessionStartIn | None = None,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    live_id = (body.live_session_id if body else "") or None
    try:
        raw = await start_speaking_session(
            db,
            student_id=student.id,
            language_id=1,
            live_session_id=live_id or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc), "code": "session_start_failed"}) from exc
    await db.commit()
    act_raw = raw.get("current_activity") or {}
    alex_raw = raw.get("alex_context") or {}
    return SpeakingSessionStartOut(
        session_id=str(raw.get("session_id", "")),
        live_session_id=str(raw.get("live_session_id", "")),
        blueprint_id=str(raw.get("blueprint_id", "")),
        phase=str(raw.get("phase", "")),
        current_activity=SpeakingSessionActivityOut.model_validate(act_raw) if act_raw else None,
        alex_context=SpeakingAlexContextOut.model_validate(alex_raw) if alex_raw else None,
        target_skill_ids=[str(x) for x in (raw.get("target_skill_ids") or [])],
        task_prompt=str(raw.get("task_prompt", "")),
    )


@router.post("/speaking/journey/session/activity/complete")
async def speaking_activity_complete(
    body: SpeakingActivityCompleteIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    try:
        raw = await complete_speaking_activity(
            db,
            student_id=student.id,
            language_id=1,
            activity_id=body.activity_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc), "code": "activity_complete_failed"}) from exc
    await db.commit()
    return raw


@router.post("/speaking/journey/session/prepare-live", response_model=SpeakingSessionStartOut)
async def speaking_session_prepare_live(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Advance the active session cursor to the first live-Alex executable task.

    Owns the pre-Talk-with-Alex positioning decision so Vue stays projection-only.
    """
    try:
        raw = await prepare_speaking_session_for_live(
            db,
            student_id=student.id,
            language_id=1,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"message": str(exc), "code": "prepare_live_failed"},
        ) from exc
    await db.commit()
    act_raw = raw.get("current_activity") or {}
    alex_raw = raw.get("alex_context") or {}
    return SpeakingSessionStartOut(
        session_id=str(raw.get("session_id", "")),
        live_session_id=str(raw.get("live_session_id", "")),
        blueprint_id=str(raw.get("blueprint_id", "")),
        phase=str(raw.get("phase", "")),
        current_activity=SpeakingSessionActivityOut.model_validate(act_raw) if act_raw else None,
        alex_context=SpeakingAlexContextOut.model_validate(alex_raw) if alex_raw else None,
        target_skill_ids=[str(x) for x in (raw.get("target_skill_ids") or [])],
        task_prompt=str(raw.get("task_prompt", "")),
    )


@router.post("/speaking/journey/session/turn")
async def speaking_session_turn(
    body: SpeakingSessionTurnIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    try:
        raw = await record_speaking_session_turn(
            db,
            student_id=student.id,
            language_id=1,
            live_turn_id=body.live_turn_id,
            performance=body.performance,
            success=body.success,
            source_dimension=body.source_dimension,
            mistake_tags=tuple(body.mistake_tags),
            mutation_applied=body.mutation_applied,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc), "code": "session_turn_failed"}) from exc
    await db.commit()
    return raw


@router.post("/speaking/journey/session/finalize", response_model=SpeakingSessionOutcomeOut)
async def speaking_session_finalize(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    try:
        raw = await finalize_speaking_session(db, student_id=student.id, language_id=1)
        # S16: post-finalize stage gate — API orchestration (not journey→progression import).
        await run_speaking_progression_engines(db, student_id=student.id, language_id=1)
        refreshed = await get_speaking_journey(db, student_id=student.id, language_id=1)
        raw["journey"] = refreshed.to_student_dict()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc), "code": "session_finalize_failed"}) from exc
    await db.commit()
    journey = raw.get("journey")
    return SpeakingSessionOutcomeOut(
        session_id=str(raw.get("session_id", "")),
        outcome_kind=str(raw.get("outcome_kind", "")),
        student_summary=str(raw.get("student_summary", "")),
        retry_same_target=bool(raw.get("retry_same_target")),
        journey=_journey_out(journey) if isinstance(journey, dict) else None,
    )
