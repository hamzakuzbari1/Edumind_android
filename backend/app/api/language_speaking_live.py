"""Speaking S7.5/S7.6/S13 — Hume EVI live conversation API endpoints.

S13: POST /speaking/live/token is the single budget authorization boundary.
No unrestricted legacy token bypass remains — credentials are minted only
after authorize_live_session succeeds.
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services.language_access_service import require_language_learning_ready
from app.services.language_rate_limit_service import check_or_raise
from app.services.language_speaking_evaluation_runtime.live_runtime import (
    get_evi_client_token,
    process_completed_live_turn,
)
from app.services.language_speaking_evaluator.input_types import (
    SpeakingGoalContext,
    SpeakingOfficialCefrContext,
    SpeakingTaskContext,
)
from app.services.language_speaking_journey.api_service import build_alex_context_for_student
from app.services.language_speaking_journey.errors import (
    SpeakingContextUnavailableError,
    SpeakingLiveExecutionError,
)
from app.services.language_speaking_journey.live_execution import authorize_live_turn_execution
from app.services.language_speaking_live_budget import (
    HEARTBEAT_INTERVAL_SECONDS,
    BudgetStateUnavailableError,
    ConversationAlreadyActiveError,
    DailyLimitReachedError,
    InvalidOrExpiredLiveLeaseError,
    LiveBudgetError,
    LiveLeaseNotOwnedError,
    authorize_live_session,
    end_live_session,
    heartbeat_live_session,
)
from app.services.language_speaking_live_conversation.errors import SpeakingLiveRuntimeError

router = APIRouter(prefix="/student/languages", tags=["Speaking Live EVI"])


class SpeakingLiveTokenIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lease_id: str | None = None


class SpeakingLiveTokenOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    expires_in: int
    config_id: str
    token_type: str = "Bearer"
    provider: str = "hume_evi"
    api_version: str = "v0"
    ws_url: str = "wss://api.hume.ai/v0/evi/chat"
    # S13 server-authoritative budget / lease fields (student-safe).
    lease_id: str = ""
    daily_limit_seconds: int = 600
    remaining_seconds: int = 0
    session_allowed_seconds: int = 0
    consumed_seconds: int = 0
    reset_at_utc: str = ""
    heartbeat_interval_seconds: int = HEARTBEAT_INTERVAL_SECONDS
    resumed: bool = False
    # S14 backend-authoritative live identity + deterministic educational grounding.
    live_session_id: str = ""
    context_version: str = ""
    context_fingerprint: str = ""
    alex_context: dict = Field(default_factory=dict)


class SpeakingLiveLeaseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lease_id: str


class SpeakingLiveHeartbeatOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lease_id: str
    charged_seconds: int = 0
    lease_accounted_seconds: int = 0
    deadline_reached: bool = False
    daily_limit_seconds: int = 600
    remaining_seconds: int = 0
    session_allowed_seconds: int = 0
    consumed_seconds: int = 0
    reset_at_utc: str = ""


class SpeakingLiveEndOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lease_id: str
    charged_seconds: int = 0
    daily_limit_seconds: int = 600
    remaining_seconds: int = 0
    session_allowed_seconds: int = 0
    consumed_seconds: int = 0
    reset_at_utc: str = ""


class SpeakingStudentSessionDimensionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = ""
    label: str = ""
    status: str = ""
    reason: str = ""


class SpeakingStudentSessionSummaryOut(BaseModel):
    """Student-safe turn summary — no scores or internal IDs."""

    model_config = ConfigDict(extra="forbid")

    coach_summary: str = ""
    focus_label: str = ""
    priority_issue: str = ""
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    dimensions: list[SpeakingStudentSessionDimensionOut] = Field(default_factory=list)
    since_last_time: str = ""
    ready_to_continue: bool = False
    can_complete: bool = False
    completion_note: str = ""
    display_version: str = "0.1.0"


class SpeakingLiveTurnOut(BaseModel):

    success: bool

    live_session_id: str = ""

    live_turn_id: str = ""

    engine_version: str = ""

    evaluation: dict = Field(default_factory=dict)

    live_conversation_evidence: dict = Field(default_factory=dict)

    provenance_trace: dict = Field(default_factory=dict)

    error: str = ""

    error_code: str = ""

    mutation_status: str = ""

    student_session_summary: SpeakingStudentSessionSummaryOut | None = None


class SpeakingLiveToolIn(BaseModel):

    tool_name: str

    tool_call_id: str

    parameters: str = "{}"

    speaking_goal: str = "general_english"


class SpeakingLiveToolOut(BaseModel):

    tool_call_id: str

    content: str

    tool_name: str = ""


def _translate_live_error(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, SpeakingLiveRuntimeError):
        return str(exc), exc.code
    return "Live conversation request failed", "live_runtime_error"


def _budget_http(exc: LiveBudgetError) -> HTTPException:
    status = 403
    if isinstance(exc, DailyLimitReachedError):
        status = 429
    elif isinstance(exc, ConversationAlreadyActiveError):
        status = 409
    elif isinstance(exc, (InvalidOrExpiredLiveLeaseError, LiveLeaseNotOwnedError)):
        status = 403
    elif isinstance(exc, BudgetStateUnavailableError):
        status = 503
    return HTTPException(
        status_code=status,
        detail={"message": exc.student_message, "code": exc.code},
    )


@router.post("/speaking/live/token", response_model=SpeakingLiveTokenOut)
async def speaking_live_token(
    body: SpeakingLiveTokenIn | None = None,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Budget-gated live authorization — mint token only after lease succeeds.

    Never returns API/secret keys. Never trusts client-reported duration.
    """
    continuity = (body.lease_id if body else None) or None
    try:
        auth = await authorize_live_session(
            db,
            student_id=student.id,
            continuity_lease_id=continuity,
        )
    except LiveBudgetError as exc:
        await db.commit()
        raise _budget_http(exc) from exc

    try:
        payload = get_evi_client_token()
    except Exception as exc:
        # Authorization succeeded but mint failed — end the lease so it cannot
        # zombie-block the student.
        try:
            await end_live_session(db, student_id=student.id, lease_id=auth.lease_id)
        except Exception:
            pass
        await db.commit()
        msg, code = _translate_live_error(exc)
        raise HTTPException(status_code=503, detail={"message": msg, "code": code}) from exc

    # S14: deterministic educational grounding is REQUIRED before an Alex session.
    # Fail closed — never hand out a live token for a generic (ungrounded) Alex chat.
    from app.services.language_speaking_journey.live_execution import derive_live_session_id

    live_session_id = derive_live_session_id(auth.lease_id)
    try:
        alex_ctx = await build_alex_context_for_student(db, student_id=student.id, language_id=1)
    except SpeakingLiveExecutionError as exc:
        # Release the lease so a missing lesson can't zombie-block the daily budget.
        try:
            await end_live_session(db, student_id=student.id, lease_id=auth.lease_id)
        except Exception:
            pass
        await db.commit()
        raise HTTPException(
            status_code=exc.http_status,
            detail={"message": exc.student_message, "code": exc.code},
        ) from exc

    # Bind lease-derived live identity onto the active S9 session (when one exists).
    from app.services.language_speaking_journey.api_service import bind_active_session_live_id

    await bind_active_session_live_id(
        db,
        student_id=student.id,
        language_id=1,
        live_session_id=live_session_id,
    )

    await db.commit()
    token_fields = {k: payload[k] for k in ("access_token", "expires_in", "config_id", "token_type", "provider", "api_version") if k in payload}
    return SpeakingLiveTokenOut(
        **token_fields,
        lease_id=auth.lease_id,
        daily_limit_seconds=auth.budget.daily_limit_seconds,
        remaining_seconds=auth.budget.remaining_seconds,
        session_allowed_seconds=auth.budget.session_allowed_seconds,
        consumed_seconds=auth.budget.consumed_seconds,
        reset_at_utc=auth.budget.reset_at_utc,
        heartbeat_interval_seconds=HEARTBEAT_INTERVAL_SECONDS,
        resumed=auth.resumed,
        live_session_id=live_session_id,
        context_version=alex_ctx.context_version,
        context_fingerprint=alex_ctx.context_fingerprint,
        alex_context=alex_ctx.to_tutor_dict(),
    )


@router.post("/speaking/live/heartbeat", response_model=SpeakingLiveHeartbeatOut)
async def speaking_live_heartbeat(
    body: SpeakingLiveLeaseIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Server-derived elapsed accounting. Client must not submit duration."""
    try:
        result = await heartbeat_live_session(
            db,
            student_id=student.id,
            lease_id=body.lease_id,
        )
    except LiveBudgetError as exc:
        await db.commit()
        raise _budget_http(exc) from exc
    await db.commit()
    return SpeakingLiveHeartbeatOut(
        lease_id=result.lease_id,
        charged_seconds=result.charged_seconds,
        lease_accounted_seconds=result.lease_accounted_seconds,
        deadline_reached=result.deadline_reached,
        daily_limit_seconds=result.budget.daily_limit_seconds,
        remaining_seconds=result.budget.remaining_seconds,
        session_allowed_seconds=result.budget.session_allowed_seconds,
        consumed_seconds=result.budget.consumed_seconds,
        reset_at_utc=result.budget.reset_at_utc,
    )


@router.post("/speaking/live/end", response_model=SpeakingLiveEndOut)
async def speaking_live_end(
    body: SpeakingLiveLeaseIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Intentional end — reconcile remaining server-elapsed time under the lease."""
    try:
        result = await end_live_session(
            db,
            student_id=student.id,
            lease_id=body.lease_id,
        )
    except LiveBudgetError as exc:
        await db.commit()
        raise _budget_http(exc) from exc
    await db.commit()
    return SpeakingLiveEndOut(
        lease_id=result.lease_id,
        charged_seconds=result.charged_seconds,
        daily_limit_seconds=result.budget.daily_limit_seconds,
        remaining_seconds=result.budget.remaining_seconds,
        session_allowed_seconds=result.budget.session_allowed_seconds,
        consumed_seconds=result.budget.consumed_seconds,
        reset_at_utc=result.budget.reset_at_utc,
    )


@router.post("/speaking/live/tool", response_model=SpeakingLiveToolOut)
async def speaking_live_tool(
    body: SpeakingLiveToolIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Relay authenticated EVI tool execution — identity from JWT only.

    S14: ``get_student_speaking_context`` reuses the SAME canonical Alex context
    builder as session-start injection (no duplicate context logic). Typed/versioned,
    no internal ids / mastery / secrets. Fails closed — never returns a generic
    "just chat" context when educational grounding is unavailable.
    """
    check_or_raise("speaking", student.id)
    tool_name = body.tool_name.strip()
    if tool_name != "get_student_speaking_context":
        raise HTTPException(
            status_code=400,
            detail={"message": "This tool is not available.", "code": "unknown_tool"},
        )
    try:
        alex_ctx = await build_alex_context_for_student(db, student_id=student.id, language_id=1)
    except SpeakingLiveExecutionError as exc:
        await db.commit()
        raise HTTPException(
            status_code=exc.http_status,
            detail={"message": exc.student_message, "code": exc.code},
        ) from exc
    except Exception as exc:
        msg, code = _translate_live_error(exc)
        raise HTTPException(status_code=503, detail={"message": msg, "code": code}) from exc

    await db.commit()
    return SpeakingLiveToolOut(
        tool_call_id=body.tool_call_id.strip(),
        content=json.dumps(alex_ctx.to_tutor_dict(), ensure_ascii=False, separators=(",", ":")),
        tool_name=tool_name,
    )


@router.post("/speaking/live/turn", response_model=SpeakingLiveTurnOut)
async def speaking_live_turn(
    file: UploadFile = File(...),
    lease_id: str = Form(default=""),
    live_session_id: str = Form(default=""),
    live_turn_id: str = Form(default=""),
    evi_events_json: str = Form(default="[]"),
    provider_transcript: str = Form(default=""),
    task_type: str = Form(default="free_speech"),
    official_cefr: str = Form(default="B1"),
    speaking_goal: str = Form(default="general_english"),
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    check_or_raise("speaking", student.id)
    turn_id = live_turn_id or f"turn-{uuid.uuid4().hex[:8]}"

    # S14 PART 14/15: pre-evaluation execution authorization boundary. A forged /
    # stale / mismatched live_session_id (or an invalid lease) is rejected HERE,
    # BEFORE the S4->S8 evaluation & knowledge-mutation path runs. The task prompt
    # is taken from backend authority — the client cannot override it.
    try:
        authz = await authorize_live_turn_execution(
            db,
            student_id=student.id,
            language_id=1,
            lease_id=lease_id,
            live_session_id=live_session_id,
        )
    except SpeakingLiveExecutionError as exc:
        await db.commit()
        return SpeakingLiveTurnOut(success=False, error=exc.student_message, error_code=exc.code)

    session_id = authz.live_session_id
    audio_bytes = await file.read()
    content_type = file.content_type or "audio/wav"

    task = SpeakingTaskContext(
        task_id=authz.task_id or f"live-task-{turn_id}",
        task_type=task_type,
        task_prompt=authz.task_prompt,
        task_instructions="Live EVI conversation turn — evaluated via canonical S4-S7 pipeline.",
        success_criteria=("Respond naturally to the conversation",),
        target_skill_ids=(),
    )
    goal = SpeakingGoalContext(speaking_goal=speaking_goal, goal_label=speaking_goal.replace("_", " ").title())
    cefr = SpeakingOfficialCefrContext(official_cefr=official_cefr)

    try:
        result = await process_completed_live_turn(
            live_session_id=session_id,
            live_turn_id=turn_id,
            student_id=student.id,
            language_id=1,
            audio_bytes=audio_bytes,
            audio_content_type=content_type,
            evi_events_json=evi_events_json,
            provider_transcript=provider_transcript,
            task=task,
            goal=goal,
            official_cefr=cefr,
            db=db,
        )
    except Exception as exc:
        msg, code = _translate_live_error(exc)
        await db.commit()
        return SpeakingLiveTurnOut(success=False, error=msg, error_code=code)

    await db.commit()
    if not result.success:
        return SpeakingLiveTurnOut(
            success=False,
            live_session_id=session_id,
            live_turn_id=turn_id,
            error=result.error,
            error_code=result.error_code or "live_evaluation_handoff_failed",
        )

    eval_block = result.evaluation_persistence.get("engine_result") or result.evaluation_persistence
    live_evidence = result.evaluation_persistence.get("live_conversation_evidence") or {}
    if result.live_turn:
        live_evidence = result.live_turn.evi_evidence.to_dict()

    summary_raw = result.student_session_summary or result.evaluation_persistence.get("student_session_summary")
    student_summary = None
    if isinstance(summary_raw, dict) and summary_raw:
        student_summary = SpeakingStudentSessionSummaryOut.model_validate(summary_raw)

    # S9: accumulate turn in active learning session (orchestration only — S8 mutation already applied).
    try:
        from app.services.language_speaking_journey.api_service import record_speaking_session_turn

        eval_block_dict = eval_block if isinstance(eval_block, dict) else {}
        candidates = eval_block_dict.get("candidate_skill_evidence") or []
        primary_perf = 0.5
        primary_success = False
        source_dim = ""
        mistake_tags: list[str] = []
        if isinstance(candidates, list) and candidates:
            first = candidates[0] if isinstance(candidates[0], dict) else {}
            primary_perf = float(first.get("performance", 0.5))
            primary_success = bool(first.get("success", False))
            source_dim = str(first.get("source_dimension", ""))
            mistake_tags = [str(x) for x in (first.get("mistake_tags") or [])]
        await record_speaking_session_turn(
            db,
            student_id=student.id,
            language_id=1,
            live_turn_id=turn_id,
            performance=primary_perf,
            success=primary_success,
            source_dimension=source_dim,
            mistake_tags=tuple(mistake_tags),
            mutation_applied=result.mutation_status == "applied",
            evaluation_id=str(eval_block_dict.get("evaluation_id") or ""),
        )
    except ValueError:
        pass
    except Exception:
        pass

    return SpeakingLiveTurnOut(
        success=True,
        live_session_id=session_id,
        live_turn_id=turn_id,
        engine_version=result.engine_version,
        evaluation=eval_block if isinstance(eval_block, dict) else {},
        live_conversation_evidence=live_evidence if isinstance(live_evidence, dict) else {},
        provenance_trace=result.provenance_trace,
        mutation_status=result.mutation_status,
        student_session_summary=student_summary,
    )
