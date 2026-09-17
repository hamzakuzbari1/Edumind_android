"""Speaking journey API orchestration (S9 + S11 attempt lineage wiring)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.progression import LanguageProgression
from app.services.language_speaking.enums import SpeakingExecutionMode
from app.services.language_progression_service import ensure_progression_row
from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_diagnostic.selector import select_speaking_target
from app.services.language_speaking_journey.alex_context import (
    AlexSpeakingEducationalContext,
    build_alex_speaking_educational_context,
)
from app.services.language_speaking_journey.builder import build_speaking_journey_bundle
from app.services.language_speaking_journey.types import SpeakingJourneyBundle
from app.services.language_speaking_knowledge_model.storage import (
    knowledge_model_from_speaking_bucket,
    speaking_bucket_from_payload,
)
from app.services.language_speaking_lesson_planner.attempt_lineage import (
    SpeakingSessionAttemptLineage,
    get_active_attempt,
    mark_active_attempt_for_outcome,
    reconcile_active_attempt_on_cursor_leave,
    start_or_resume_attempt,
)
from app.services.language_speaking_lesson_planner.decision_rules import mission_flow_from_session_outcome
from app.services.language_speaking_lesson_planner.mission_task_resolver import resolve_current_task
from app.services.language_speaking_lesson_planner.planner import assemble_speaking_lesson_blueprint
from app.services.language_speaking_lesson_planner.session_runtime import (
    advance_session_activity,
    create_learning_session,
    evaluate_session_boundary,
    record_session_turn,
    student_safe_activity,
)
from app.services.language_speaking_lesson_planner.storage import (
    ACTIVE_BLUEPRINT_KEY,
    ATTEMPT_LINEAGE_KEY,
    LEARNING_PLAN_KEY,
    LEARNING_SESSION_KEY,
    load_s9_state,
    merge_speaking_bucket_into_payload,
    save_s9_state,
)
from app.services.language_speaking_lesson_planner.types import (
    SpeakingLearningPlan,
    SpeakingSessionPhase,
)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


async def _load_row(db: AsyncSession, *, student_id: int, language_id: int) -> LanguageProgression:
    row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        row = LanguageProgression(
            student_id=student_id,
            language_id=language_id,
            promotion_readiness_json={},
        )
        db.add(row)
        await db.flush()
    return row


def _student_promotion_projection(row) -> dict[str, object] | None:
    payload = dict(getattr(row, "promotion_readiness_json", None) or {})
    bucket = payload.get("speaking_promotion")
    if not isinstance(bucket, dict):
        return None
    proj = bucket.get("student_projection")
    return dict(proj) if isinstance(proj, dict) else None


def _official_cefr(row: LanguageProgression) -> str:
    val = row.official_speaking_cefr
    return val.value if hasattr(val, "value") else str(val or "A2")


def _blueprint_matches_official_cefr(blueprint, official_cefr: str) -> bool:
    if blueprint is None:
        return True
    return str(getattr(blueprint, "official_cefr_hint", "") or "").upper() == official_cefr.upper()


def _clear_stale_s9_state(bucket: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(bucket)
    for key in (LEARNING_PLAN_KEY, ACTIVE_BLUEPRINT_KEY, LEARNING_SESSION_KEY, ATTEMPT_LINEAGE_KEY):
        cleaned.pop(key, None)
    return cleaned


def _ensure_lineage(lineage: SpeakingSessionAttemptLineage | None, session_id: str) -> SpeakingSessionAttemptLineage:
    if lineage is None or lineage.session_id != session_id:
        return SpeakingSessionAttemptLineage.empty_for_session(session_id)
    return lineage


async def get_speaking_journey(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
    speaking_goal: str = "general_english",
) -> SpeakingJourneyBundle:
    row = await _load_row(db, student_id=student_id, language_id=language_id)
    payload = dict(row.promotion_readiness_json or {})
    bucket = speaking_bucket_from_payload(payload)
    state = load_s9_state(bucket)
    plan, blueprint, session, lineage = state.plan, state.blueprint, state.session, state.attempt_lineage
    official = _official_cefr(row)

    if not _blueprint_matches_official_cefr(blueprint, official):
        bucket = _clear_stale_s9_state(bucket)
        plan, blueprint, session, lineage = None, None, None, None

    if plan is None or blueprint is None:
        km = knowledge_model_from_speaking_bucket(bucket, student_id=student_id, language_id=language_id)
        rec = select_speaking_target(
            km,
            official_cefr=official,
            speaking_goal=speaking_goal,
        )
        blueprint = assemble_speaking_lesson_blueprint(rec)
        node = SPEAKING_SKILL_GRAPH.node_by_id(blueprint.primary_target_skill_id)
        plan = SpeakingLearningPlan(
            plan_id=f"slp-{uuid.uuid4().hex[:10]}",
            active_blueprint_id=blueprint.blueprint_id,
            primary_target_skill_id=blueprint.primary_target_skill_id,
            primary_target_label=node.label if node else blueprint.primary_target_skill_id,
            selection_reason=blueprint.selection_reason,
            updated_at=_now_iso(),
        )
        bucket = save_s9_state(bucket, plan=plan, blueprint=blueprint)
        payload = merge_speaking_bucket_into_payload(payload, bucket)
        row.promotion_readiness_json = payload
        flag_modified(row, "promotion_readiness_json")

    alex_remaining: int | None = None
    try:
        from app.services.language_speaking_live_budget import (
            BudgetStateUnavailableError,
            read_daily_budget,
        )

        budget = await read_daily_budget(db, student_id=student_id)
        alex_remaining = int(budget.remaining_seconds)
    except BudgetStateUnavailableError:
        alex_remaining = None
    except Exception:
        alex_remaining = None

    return build_speaking_journey_bundle(
        official_level=official,
        plan=plan,
        blueprint=blueprint,
        session=session,
        attempt_lineage=lineage,
        knowledge_model=knowledge_model_from_speaking_bucket(bucket, student_id=student_id, language_id=language_id),
        alex_daily_remaining_seconds=alex_remaining,
        learning_stage_speaking=getattr(row, "learning_stage_speaking", None),
        promotion_readiness=_student_promotion_projection(row),
    )


async def start_speaking_session(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
    live_session_id: str | None = None,
    speaking_goal: str = "general_english",
) -> dict[str, Any]:
    row = await _load_row(db, student_id=student_id, language_id=language_id)
    payload = dict(row.promotion_readiness_json or {})
    bucket = speaking_bucket_from_payload(payload)
    state = load_s9_state(bucket)
    plan, blueprint, existing, lineage = state.plan, state.blueprint, state.session, state.attempt_lineage
    if not _blueprint_matches_official_cefr(blueprint, _official_cefr(row)):
        bucket = _clear_stale_s9_state(bucket)
        payload = merge_speaking_bucket_into_payload(payload, bucket)
        row.promotion_readiness_json = payload
        flag_modified(row, "promotion_readiness_json")
        await get_speaking_journey(
            db,
            student_id=student_id,
            language_id=language_id,
            speaking_goal=speaking_goal,
        )
        payload = dict(row.promotion_readiness_json or {})
        bucket = speaking_bucket_from_payload(payload)
        state = load_s9_state(bucket)
        plan, blueprint, existing, lineage = (
            state.plan,
            state.blueprint,
            state.session,
            state.attempt_lineage,
        )
    if blueprint is None:
        raise ValueError("no_active_blueprint")

    resumed = False
    if existing and existing.phase != SpeakingSessionPhase.completed:
        session = existing
        resumed = True
    else:
        session = create_learning_session(blueprint, live_session_id=live_session_id)

    lineage = _ensure_lineage(lineage, session.session_id)
    resolution = resolve_current_task(blueprint, session)
    attempt_summary: dict[str, object] = {}
    if resolution.is_task:
        attempt = start_or_resume_attempt(
            lineage,
            resolution,
            session_id=session.session_id,
            blueprint_id=blueprint.blueprint_id,
            is_resume=resumed,
            live_session_id=live_session_id or session.live_session_id,
        )
        attempt_summary = {
            "attempt_id": attempt.attempt_id,
            "attempt_number": attempt.attempt_number,
            "task_id": attempt.task_id,
            "mission_id": attempt.mission_id,
            "is_retry": attempt.is_retry,
        }

    bucket = save_s9_state(bucket, session=session, attempt_lineage=lineage)
    payload = merge_speaking_bucket_into_payload(payload, bucket)
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")

    return _session_start_payload(
        blueprint=blueprint,
        session=session,
        resolution=resolution,
        attempt_summary=attempt_summary,
    )


def _session_start_payload(
    *,
    blueprint,
    session,
    resolution,
    attempt_summary: dict[str, object] | None = None,
) -> dict[str, Any]:
    activity = student_safe_activity(blueprint, session.current_activity_id)
    return {
        "session_id": session.session_id,
        "live_session_id": session.live_session_id,
        "blueprint_id": blueprint.blueprint_id,
        "phase": session.phase.value,
        "current_activity": activity,
        "alex_context": blueprint.alex_context.to_dict(),
        "target_skill_ids": list(blueprint.target_skill_ids),
        "task_prompt": blueprint.alex_context.communicative_scenario,
        "task_resolution": resolution.to_dict(),
        "attempt": attempt_summary or {},
        "live_execution_ready": (
            resolution.is_task
            and resolution.execution_mode == SpeakingExecutionMode.live_evi_conversation.value
        ),
    }


async def prepare_speaking_session_for_live(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
) -> dict[str, Any]:
    """Ensure an active session and advance the cursor to the first live-Alex task.

    Completes non-live activities server-side so Talk-with-Alex entry does not invent
    educational decisions in Vue. The normal lesson Continue path still advances
    one activity at a time via ``complete_speaking_activity``.
    """
    await start_speaking_session(db, student_id=student_id, language_id=language_id)
    row = await _load_row(db, student_id=student_id, language_id=language_id)
    payload = dict(row.promotion_readiness_json or {})
    bucket = speaking_bucket_from_payload(payload)
    state = load_s9_state(bucket)
    blueprint, session, lineage = state.blueprint, state.session, state.attempt_lineage
    if blueprint is None or session is None:
        raise ValueError("no_active_session")

    max_advances = max(1, len(blueprint.activities) + 2)
    for _ in range(max_advances):
        resolution = resolve_current_task(blueprint, session)
        if (
            resolution.is_task
            and resolution.execution_mode == SpeakingExecutionMode.live_evi_conversation.value
        ):
            lineage = _ensure_lineage(lineage, session.session_id)
            attempt = start_or_resume_attempt(
                lineage,
                resolution,
                session_id=session.session_id,
                blueprint_id=blueprint.blueprint_id,
                is_resume=True,
                live_session_id=session.live_session_id,
            )
            bucket = save_s9_state(bucket, session=session, attempt_lineage=lineage)
            payload = merge_speaking_bucket_into_payload(payload, bucket)
            row.promotion_readiness_json = payload
            flag_modified(row, "promotion_readiness_json")
            return _session_start_payload(
                blueprint=blueprint,
                session=session,
                resolution=resolution,
                attempt_summary={
                    "attempt_id": attempt.attempt_id,
                    "attempt_number": attempt.attempt_number,
                    "task_id": attempt.task_id,
                    "mission_id": attempt.mission_id,
                    "is_retry": attempt.is_retry,
                },
            )

        activity_id = session.current_activity_id
        if not activity_id:
            raise ValueError("no_live_activity_available")
        before = activity_id
        session = advance_session_activity(session, blueprint, completed_activity_id=activity_id)
        lineage = _ensure_lineage(lineage, session.session_id)
        resolution = resolve_current_task(blueprint, session)
        reconcile_active_attempt_on_cursor_leave(
            lineage,
            current_task_id=resolution.task_id if resolution.is_task else "",
        )
        if session.current_activity_id == before:
            raise ValueError("no_live_activity_available")

    raise ValueError("no_live_activity_available")


async def bind_active_session_live_id(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    live_session_id: str,
) -> None:
    """Persist the backend-issued live conversation id onto the active S9 session."""
    if not live_session_id:
        return
    row = await _load_row(db, student_id=student_id, language_id=language_id)
    payload = dict(row.promotion_readiness_json or {})
    bucket = speaking_bucket_from_payload(payload)
    state = load_s9_state(bucket)
    session = state.session
    if session is None or session.phase == SpeakingSessionPhase.completed:
        return
    if session.live_session_id == live_session_id:
        return
    session.live_session_id = live_session_id
    session.updated_at = _now_iso()
    bucket = save_s9_state(bucket, session=session)
    payload = merge_speaking_bucket_into_payload(payload, bucket)
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")


async def complete_speaking_activity(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    activity_id: str,
) -> dict[str, Any]:
    row = await _load_row(db, student_id=student_id, language_id=language_id)
    payload = dict(row.promotion_readiness_json or {})
    bucket = speaking_bucket_from_payload(payload)
    state = load_s9_state(bucket)
    blueprint, session, lineage = state.blueprint, state.session, state.attempt_lineage
    if blueprint is None or session is None:
        raise ValueError("no_active_session")
    session = advance_session_activity(session, blueprint, completed_activity_id=activity_id)

    # When advancing onto a new executable task, start its attempt lineage (D).
    lineage = _ensure_lineage(lineage, session.session_id)
    resolution = resolve_current_task(blueprint, session)
    # S14 C-3: cursor left the previous task (to a non-task activity OR a different
    # task). The prior active attempt must not remain accidentally active.
    reconcile_active_attempt_on_cursor_leave(
        lineage,
        current_task_id=resolution.task_id if resolution.is_task else "",
    )
    if resolution.is_task:
        active = get_active_attempt(lineage)
        if active is None or active.task_id != resolution.task_id:
            start_or_resume_attempt(
                lineage,
                resolution,
                session_id=session.session_id,
                blueprint_id=blueprint.blueprint_id,
                is_resume=False,
                live_session_id=session.live_session_id,
                force_new=True,
            )

    bucket = save_s9_state(bucket, session=session, attempt_lineage=lineage)
    payload = merge_speaking_bucket_into_payload(payload, bucket)
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")
    return {
        "session_id": session.session_id,
        "phase": session.phase.value,
        "current_activity": student_safe_activity(blueprint, session.current_activity_id),
        "task_resolution": resolution.to_dict(),
    }


async def record_speaking_session_turn(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    live_turn_id: str,
    performance: float,
    success: bool,
    source_dimension: str,
    mistake_tags: tuple[str, ...],
    mutation_applied: bool,
    evaluation_id: str = "",
    is_resume: bool = False,
) -> dict[str, Any]:
    row = await _load_row(db, student_id=student_id, language_id=language_id)
    payload = dict(row.promotion_readiness_json or {})
    bucket = speaking_bucket_from_payload(payload)
    state = load_s9_state(bucket)
    blueprint, session, lineage = state.blueprint, state.session, state.attempt_lineage
    if blueprint is None or session is None:
        raise ValueError("no_active_session")

    # Idempotent turn accumulation: skip duplicate live_turn_id in session turns.
    already_recorded = any(t.live_turn_id == live_turn_id for t in session.turn_accumulations)
    if not already_recorded:
        session = record_session_turn(
            session,
            live_turn_id=live_turn_id,
            target_skill_id=blueprint.primary_target_skill_id,
            performance=performance,
            success=success,
            source_dimension=source_dimension,
            mistake_tags=mistake_tags,
            mutation_applied=mutation_applied,
        )

    lineage = _ensure_lineage(lineage, session.session_id)
    resolution = resolve_current_task(blueprint, session)
    attempt_id = ""
    attempt_number = 0
    if resolution.is_task:
        attempt = start_or_resume_attempt(
            lineage,
            resolution,
            session_id=session.session_id,
            blueprint_id=blueprint.blueprint_id,
            is_resume=is_resume,
            live_session_id=session.live_session_id,
        )
        attempt.attach_turn(live_turn_id)
        if evaluation_id:
            attempt.attach_evaluation(evaluation_id)
        attempt_id = attempt.attempt_id
        attempt_number = attempt.attempt_number

    bucket = save_s9_state(bucket, session=session, attempt_lineage=lineage)
    payload = merge_speaking_bucket_into_payload(payload, bucket)
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")
    return {
        "session_id": session.session_id,
        "communicative_turns_completed": session.communicative_turns_completed,
        "phase": session.phase.value,
        "attempt_id": attempt_id,
        "attempt_number": attempt_number,
        "task_id": resolution.task_id if resolution.is_task else "",
    }


async def finalize_speaking_session(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> dict[str, Any]:
    row = await _load_row(db, student_id=student_id, language_id=language_id)
    payload = dict(row.promotion_readiness_json or {})
    bucket = speaking_bucket_from_payload(payload)
    state = load_s9_state(bucket)
    plan, blueprint, session, lineage = state.plan, state.blueprint, state.session, state.attempt_lineage
    if blueprint is None or session is None:
        raise ValueError("no_active_session")
    decision = evaluate_session_boundary(session, blueprint)
    session.phase = SpeakingSessionPhase.completed

    lineage = _ensure_lineage(lineage, session.session_id)
    mission_outcome = mission_flow_from_session_outcome(decision.outcome_kind)
    mark_active_attempt_for_outcome(lineage, mission_outcome)

    bucket = save_s9_state(bucket, session=session, attempt_lineage=lineage)
    payload = merge_speaking_bucket_into_payload(payload, bucket)
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")
    # S16 progression engines are orchestrated by the API layer after finalize
    # (journey must not import progression — S0 layer order).
    journey = build_speaking_journey_bundle(
        official_level=_official_cefr(row),
        plan=plan,
        blueprint=blueprint,
        session=session,
        attempt_lineage=lineage,
        knowledge_model=knowledge_model_from_speaking_bucket(bucket, student_id=student_id, language_id=language_id),
        learning_stage_speaking=getattr(row, "learning_stage_speaking", None),
        promotion_readiness=_student_promotion_projection(row),
    )
    return {
        "session_id": session.session_id,
        "outcome_kind": decision.outcome_kind.value,
        "mission_outcome": mission_outcome.value,
        "student_summary": decision.student_summary,
        "retry_same_target": decision.retry_same_target,
        "journey": journey.to_student_dict(),
    }


async def build_alex_context_for_student(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
) -> AlexSpeakingEducationalContext:
    """Canonical Alex educational context from authoritative DB state (S14).

    Single builder shared by session-start injection AND the tool refresh path.
    Raises typed ``SpeakingContextUnavailableError`` / ``AmbiguousActiveAttemptError``
    (fail closed) — callers MUST NOT fall back to a generic Alex conversation.
    """
    row = await _load_row(db, student_id=student_id, language_id=language_id)
    bucket = speaking_bucket_from_payload(dict(row.promotion_readiness_json or {}))
    state = load_s9_state(bucket)
    knowledge_model = knowledge_model_from_speaking_bucket(
        bucket, student_id=student_id, language_id=language_id
    )
    return build_alex_speaking_educational_context(
        official_cefr=_official_cefr(row),
        state=state,
        knowledge_model=knowledge_model,
    )


async def get_session_evi_context(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
) -> dict[str, object] | None:
    row = await _load_row(db, student_id=student_id, language_id=language_id)
    bucket = speaking_bucket_from_payload(dict(row.promotion_readiness_json or {}))
    state = load_s9_state(bucket)
    blueprint, session = state.blueprint, state.session
    if blueprint is None:
        return None
    ctx = blueprint.alex_context.to_dict()
    ctx["session_id"] = session.session_id if session else ""
    ctx["live_session_id"] = session.live_session_id if session else ""
    ctx["phase"] = session.phase.value if session else ""
    return ctx
