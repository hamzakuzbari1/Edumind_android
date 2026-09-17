"""Typed Grammar Runtime storage under promotion_readiness_json['grammar']['runtime']."""

from __future__ import annotations

from typing import Any

from app.services.language_grammar.enums import GrammarLessonStepKind, GrammarReinforcementSkill
from app.services.language_grammar.ownership import GRAMMAR_JSONB_NAMESPACE
from app.services.language_grammar.types import GRAMMAR_STORAGE_RUNTIME_KEY
from app.services.language_grammar_lesson_planner.serialization import (
    blueprint_from_dict,
    blueprint_to_dict,
)
from app.services.language_grammar_lesson_planner.types import GrammarLessonBlueprint
from app.services.language_grammar_lesson_runtime.types import (
    GRAMMAR_RUNTIME_SCHEMA_VERSION,
    GrammarEvidenceRequest,
    GrammarRuntimeCursor,
    GrammarRuntimeEvent,
    GrammarRuntimeEventType,
    GrammarRuntimeSession,
    GrammarRuntimeState,
    GrammarStepExecutionRecord,
)


def runtime_bucket_from_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    root = dict((payload or {}).get(GRAMMAR_JSONB_NAMESPACE) or {})
    return dict(root.get(GRAMMAR_STORAGE_RUNTIME_KEY) or {})


def merge_runtime_into_payload(
    payload: dict[str, Any] | None,
    bucket: dict[str, Any],
) -> dict[str, Any]:
    out = dict(payload or {})
    root = dict(out.get(GRAMMAR_JSONB_NAMESPACE) or {})
    root[GRAMMAR_STORAGE_RUNTIME_KEY] = dict(bucket)
    out[GRAMMAR_JSONB_NAMESPACE] = root
    return out


def _event_to_dict(event: GrammarRuntimeEvent) -> dict[str, Any]:
    return {
        "sequence": event.sequence,
        "event_type": event.event_type.value,
        "lesson_id": event.lesson_id,
        "at": event.at,
        "step_id": event.step_id,
        "step_kind": event.step_kind.value if event.step_kind else None,
        "detail": event.detail,
    }


def _event_from_dict(raw: dict[str, Any]) -> GrammarRuntimeEvent:
    kind_raw = raw.get("step_kind")
    return GrammarRuntimeEvent(
        sequence=int(raw["sequence"]),
        event_type=GrammarRuntimeEventType(str(raw["event_type"])),
        lesson_id=str(raw["lesson_id"]),
        at=str(raw["at"]),
        step_id=raw.get("step_id"),
        step_kind=GrammarLessonStepKind(kind_raw) if kind_raw else None,
        detail=str(raw.get("detail") or ""),
    )


def _evidence_to_dict(req: GrammarEvidenceRequest) -> dict[str, Any]:
    return {
        "step_id": req.step_id,
        "grammar_id": req.grammar_id,
        "observation_types_hint": list(req.observation_types_hint),
        "context_hint": req.context_hint,
        "skill": req.skill.value if req.skill else None,
    }


def _evidence_from_dict(raw: dict[str, Any]) -> GrammarEvidenceRequest:
    skill_raw = raw.get("skill")
    return GrammarEvidenceRequest(
        step_id=str(raw["step_id"]),
        grammar_id=str(raw["grammar_id"]),
        observation_types_hint=tuple(raw.get("observation_types_hint") or ("formative",)),
        context_hint=raw.get("context_hint"),
        skill=GrammarReinforcementSkill(skill_raw) if skill_raw else None,
    )


def _step_execution_to_dict(rec: GrammarStepExecutionRecord) -> dict[str, Any]:
    return {
        "execution_id": rec.execution_id,
        "skill_executor_id": rec.skill_executor_id,
        "activity_id": rec.activity_id,
        "step_id": rec.step_id,
        "status": rec.status,
        "lifecycle_phases": list(rec.lifecycle_phases),
        "duration_ms": rec.duration_ms,
        "started_at": rec.started_at,
        "finished_at": rec.finished_at,
        "evidence_observation_ids": list(rec.evidence_observation_ids),
        "notes": rec.notes,
    }


def _step_execution_from_dict(raw: dict[str, Any]) -> GrammarStepExecutionRecord:
    return GrammarStepExecutionRecord(
        execution_id=str(raw.get("execution_id") or ""),
        skill_executor_id=str(raw.get("skill_executor_id") or ""),
        activity_id=str(raw.get("activity_id") or ""),
        step_id=str(raw.get("step_id") or ""),
        status=str(raw.get("status") or ""),
        lifecycle_phases=tuple(raw.get("lifecycle_phases") or ()),
        duration_ms=int(raw.get("duration_ms") or 0),
        started_at=str(raw.get("started_at") or ""),
        finished_at=str(raw.get("finished_at") or ""),
        evidence_observation_ids=tuple(raw.get("evidence_observation_ids") or ()),
        notes=str(raw.get("notes") or ""),
    )


def session_from_bucket(bucket: dict[str, Any] | None) -> GrammarRuntimeSession | None:
    raw = dict(bucket or {})
    if not raw.get("lesson_id"):
        return None
    cursor_raw = dict(raw.get("cursor") or {})
    kind_raw = cursor_raw.get("current_step_kind")
    skill_raw = cursor_raw.get("current_reinforcement_skill")
    cursor = GrammarRuntimeCursor(
        blueprint_fingerprint=str(cursor_raw.get("blueprint_fingerprint") or ""),
        step_index=int(cursor_raw.get("step_index") or 0),
        current_step_id=cursor_raw.get("current_step_id"),
        current_step_kind=GrammarLessonStepKind(kind_raw) if kind_raw else None,
        current_reinforcement_skill=GrammarReinforcementSkill(skill_raw) if skill_raw else None,
    )
    events = tuple(_event_from_dict(dict(e)) for e in (raw.get("events") or []) if isinstance(e, dict))
    evidence = tuple(
        _evidence_from_dict(dict(e)) for e in (raw.get("evidence_requests") or []) if isinstance(e, dict)
    )
    step_executions = tuple(
        _step_execution_from_dict(dict(e))
        for e in (raw.get("step_executions") or [])
        if isinstance(e, dict)
    )
    return GrammarRuntimeSession(
        student_id=int(raw["student_id"]),
        language_id=int(raw["language_id"]),
        grammar_id=str(raw["grammar_id"]),
        lesson_id=str(raw["lesson_id"]),
        state=GrammarRuntimeState(str(raw["state"])),
        cursor=cursor,
        blueprint_fingerprint=str(raw.get("blueprint_fingerprint") or ""),
        completed_step_ids=tuple(raw.get("completed_step_ids") or ()),
        pending_step_ids=tuple(raw.get("pending_step_ids") or ()),
        events=events,
        evidence_requests=evidence,
        step_executions=step_executions,
        package_id=str(raw.get("package_id") or ""),
        failure_reason=raw.get("failure_reason"),
        schema_version=int(raw.get("schema_version") or GRAMMAR_RUNTIME_SCHEMA_VERSION),
        enabled=bool(raw.get("enabled", True)),
    )


def bucket_from_session(
    session: GrammarRuntimeSession,
    *,
    blueprint: GrammarLessonBlueprint | None = None,
) -> dict[str, Any]:
    """Persist session (+ optional frozen blueprint blob for replay)."""
    out: dict[str, Any] = {
        "schema_version": GRAMMAR_RUNTIME_SCHEMA_VERSION,
        "student_id": session.student_id,
        "language_id": session.language_id,
        "grammar_id": session.grammar_id,
        "lesson_id": session.lesson_id,
        "state": session.state.value,
        "lifecycle": session.lifecycle.value,
        "blueprint_fingerprint": session.blueprint_fingerprint,
        "completed_step_ids": list(session.completed_step_ids),
        "pending_step_ids": list(session.pending_step_ids),
        "package_id": session.package_id,
        "failure_reason": session.failure_reason,
        "enabled": session.enabled,
        "cursor": {
            "blueprint_fingerprint": session.cursor.blueprint_fingerprint,
            "step_index": session.cursor.step_index,
            "current_step_id": session.cursor.current_step_id,
            "current_step_kind": (
                session.cursor.current_step_kind.value if session.cursor.current_step_kind else None
            ),
            "current_reinforcement_skill": (
                session.cursor.current_reinforcement_skill.value
                if session.cursor.current_reinforcement_skill
                else None
            ),
        },
        "events": [_event_to_dict(e) for e in session.events],
        "evidence_requests": [_evidence_to_dict(e) for e in session.evidence_requests],
        "step_executions": [_step_execution_to_dict(r) for r in session.step_executions],
    }
    if blueprint is not None:
        if blueprint.fingerprint != session.blueprint_fingerprint:
            raise ValueError("Cannot persist blueprint with mismatched fingerprint")
        out["blueprint"] = blueprint_to_dict(blueprint)
    return out


def blueprint_from_runtime_bucket(bucket: dict[str, Any] | None) -> GrammarLessonBlueprint | None:
    raw = dict(bucket or {})
    bp = raw.get("blueprint")
    if not isinstance(bp, dict):
        return None
    return blueprint_from_dict(bp)
