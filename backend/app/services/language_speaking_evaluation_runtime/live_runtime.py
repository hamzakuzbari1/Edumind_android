"""S7.5 live turn handoff into frozen S4->S7 evaluation pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.language_speaking.enums import SpeakingAudioSource
from app.services.language_speaking_audio_frontend.media_adapter import artifact_from_bytes
from app.services.language_speaking_evaluation_runtime.evaluation_pipeline import process_speaking_evaluation
from app.services.language_speaking_evaluation_runtime.knowledge_bridge import (
    apply_speaking_evaluation_to_knowledge_model,
)
from app.services.language_speaking_evaluator.input_types import (
    SpeakingGoalContext,
    SpeakingOfficialCefrContext,
    SpeakingTaskContext,
)
from app.services.language_speaking_live_conversation.event_mapping import (
    extract_chat_metadata,
    extract_user_message_facts,
    map_evi_event,
)
from app.services.language_speaking_live_conversation.errors import LiveEvaluationHandoffFailedError
from app.services.language_speaking_live_conversation.types import (
    SpeakingLiveConversationEvidence,
    SpeakingLiveEvent,
    SpeakingLiveExpressionMeasure,
    SpeakingLiveTurn,
)
from app.services.language_speaking_evaluation_runtime.evi_token import mint_evi_access_token
from app.services.language_speaking_evaluation_runtime.evi_tool_runtime import invalidate_live_context
from app.services.language_speaking_explainability.student_session_summary import (
    build_speaking_student_session_summary,
)

LANGUAGE_SPEAKING_LIVE_RUNTIME_VERSION = "7.5.0"


@dataclass(frozen=True, slots=True)
class LiveTurnEvaluationResult:
    success: bool
    live_turn: SpeakingLiveTurn | None = None
    evaluation_persistence: dict[str, object] = field(default_factory=dict)
    engine_version: str = ""
    provenance_trace: dict[str, object] = field(default_factory=dict)
    error: str = ""
    error_code: str = ""
    mutation_status: str = ""
    mutation_error_code: str = ""
    applied_observation_ids: tuple[str, ...] = ()
    bridge_diagnostics: dict[str, object] = field(default_factory=dict)
    student_session_summary: dict[str, object] = field(default_factory=dict)


def build_evi_evidence_from_events(
    events: tuple[dict[str, object], ...],
    *,
    provider_transcript_override: str = "",
) -> SpeakingLiveConversationEvidence:
    mapped: list[SpeakingLiveEvent] = []
    expressions: list[SpeakingLiveExpressionMeasure] = []
    transcript = provider_transcript_override
    interruptions = 0
    chat_id = ""
    chat_group_id = ""
    timing: tuple[int, int] | None = None
    unavailable: list[str] = []

    for raw in events:
        ev = map_evi_event(raw)
        mapped.append(ev)
        et = str(raw.get("type") or "")
        if et == "user_interruption":
            interruptions += 1
        elif et == "chat_metadata":
            chat_id, chat_group_id = extract_chat_metadata(raw)
        elif et == "user_message" and not raw.get("interim"):
            t, m, tm = extract_user_message_facts(raw)
            if t:
                transcript = t
            expressions.extend(m)
            if tm:
                timing = tm

    if not expressions:
        unavailable.append("expression_measures")

    return SpeakingLiveConversationEvidence(
        provider_transcript=transcript,
        expression_measures=tuple(expressions),
        event_sequence=tuple(mapped),
        interruption_count=interruptions,
        provider_chat_id=chat_id,
        provider_chat_group_id=chat_group_id,
        turn_timing_ms=timing,
        unavailable_fields=tuple(unavailable),
    )


async def process_completed_live_turn(
    *,
    live_session_id: str,
    live_turn_id: str,
    student_id: int,
    language_id: int,
    audio_bytes: bytes,
    audio_content_type: str,
    evi_events_json: str,
    provider_transcript: str = "",
    task: SpeakingTaskContext,
    goal: SpeakingGoalContext,
    official_cefr: SpeakingOfficialCefrContext,
    revision_number: int = 1,
    started_at: str | None = None,
    ended_at: str | None = None,
    db: AsyncSession | None = None,
) -> LiveTurnEvaluationResult:
    """Hand off completed student turn audio to frozen S4->S5->S6->S7 pipeline."""
    if not audio_bytes:
        raise LiveEvaluationHandoffFailedError("Completed turn has no student audio")

    try:
        raw_events = json.loads(evi_events_json or "[]")
    except json.JSONDecodeError as exc:
        raise LiveEvaluationHandoffFailedError("Invalid EVI events JSON") from exc
    if not isinstance(raw_events, list):
        raw_events = []

    event_dicts = [e for e in raw_events if isinstance(e, dict)]
    evi_evidence = build_evi_evidence_from_events(
        tuple(event_dicts),
        provider_transcript_override=provider_transcript,
    )

    ts = datetime.now(tz=timezone.utc)
    turn = SpeakingLiveTurn(
        turn_id=live_turn_id,
        session_id=live_session_id,
        student_id=student_id,
        language_id=language_id,
        started_at=started_at or ts.isoformat(),
        ended_at=ended_at or ts.isoformat(),
        audio_bytes=audio_bytes,
        audio_content_type=audio_content_type or "audio/wav",
        provider_transcript=evi_evidence.provider_transcript,
        evi_evidence=evi_evidence,
        finalized=True,
    )

    artifact = artifact_from_bytes(
        audio_id=f"live-{live_turn_id}",
        session_id=live_session_id,
        student_id=student_id,
        language_id=language_id,
        audio_bytes=audio_bytes,
        original_filename=f"{live_turn_id}.wav",
        content_type=audio_content_type or "audio/wav",
        audio_source=SpeakingAudioSource.file_upload,
        storage_reference=f"live://{live_session_id}/{live_turn_id}",
        captured_at=ts,
    )

    eval_result = await process_speaking_evaluation(
        artifact,
        audio_bytes,
        task=task,
        goal=goal,
        official_cefr=official_cefr,
        student_id=student_id,
        language_id=language_id,
        revision_number=revision_number,
        initial_prompt=task.task_prompt,
    )

    if not eval_result.success or eval_result.evaluation is None:
        return LiveTurnEvaluationResult(
            success=False,
            live_turn=turn,
            error=eval_result.error or "S4-S7 evaluation failed",
            error_code="live_evaluation_handoff_failed",
        )

    persistence = dict(eval_result.persistence_dict)
    persistence["live_conversation_evidence"] = evi_evidence.to_dict()
    persistence["live_traceability"] = {
        "live_session_id": live_session_id,
        "live_turn_id": live_turn_id,
        "source_audio_id": artifact.audio_id,
        "runtime_version": LANGUAGE_SPEAKING_LIVE_RUNTIME_VERSION,
    }

    prov_trace: dict[str, object] = {
        "live_session_id": live_session_id,
        "live_turn_id": live_turn_id,
        "source_audio_id": artifact.audio_id,
        "s7_engine_version": eval_result.evaluation.engine_version,
        "evi_provider_chat_id": evi_evidence.provider_chat_id,
    }
    if eval_result.evaluation.evidence_summary.provider_provenance:
        prov_trace["s4_s5_s6_provenance"] = list(eval_result.evaluation.evidence_summary.provider_provenance)

    bridge_status = ""
    bridge_error = ""
    applied_ids: tuple[str, ...] = ()
    bridge_diag: dict[str, object] = {}

    if db is not None:
        bridge_result = await apply_speaking_evaluation_to_knowledge_model(
            db,
            student_id=student_id,
            language_id=language_id,
            evaluation=eval_result.evaluation,
            turn_reference=live_turn_id,
            session_id=live_session_id,
            now=ts,
        )
        bridge_status = str(bridge_result.mutation_status.value)
        bridge_error = bridge_result.mutation_error_code
        applied_ids = bridge_result.applied_observation_ids
        bridge_diag = bridge_result.bridge_diagnostics()
        prov_trace["s8_knowledge_bridge"] = bridge_diag

    invalidate_live_context(student_id=student_id, language_id=language_id)

    student_summary = build_speaking_student_session_summary(eval_result.evaluation).to_student_dict()
    persistence["student_session_summary"] = student_summary

    return LiveTurnEvaluationResult(
        success=True,
        live_turn=turn,
        evaluation_persistence=persistence,
        engine_version=eval_result.evaluation.engine_version,
        provenance_trace=prov_trace,
        mutation_status=bridge_status,
        mutation_error_code=bridge_error,
        applied_observation_ids=applied_ids,
        bridge_diagnostics=bridge_diag,
        student_session_summary=student_summary,
    )


def get_evi_client_token() -> dict[str, object]:
    """Mint browser-safe EVI access token — never returns API/secret keys."""
    return mint_evi_access_token()
