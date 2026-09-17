"""Confidence persistence via existing preferences_json (Phase 3.2)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.services.language_student_profile_service import (
    get_language_student_profile,
    get_or_create_language_student_profile,
)
from app.services.language_listening_confidence.constants import CONFIDENCE_KEY, INITIAL_CONFIDENCE
from app.services.language_listening_confidence.types import (
    ConfidenceState,
    ObjectiveConfidenceRecord,
    ObjectiveEvidenceRecord,
)
from app.services.language_listening_curriculum.objectives import level_objectives


def _evidence_from_dict(raw: dict | None) -> ObjectiveEvidenceRecord:
    ev = ObjectiveEvidenceRecord()
    if not isinstance(raw, dict):
        return ev
    for key in ("difficulty", "formats", "topics", "speakers", "speed"):
        blob = raw.get(key)
        if isinstance(blob, dict):
            setattr(ev, key, {str(k): int(v) for k, v in blob.items()})
    return ev


def _record_from_dict(oid: str, label: str, raw: dict) -> ObjectiveConfidenceRecord:
    return ObjectiveConfidenceRecord(
        objective_id=oid,
        label=label,
        confidence=float(raw.get("confidence", INITIAL_CONFIDENCE)),
        last_update_index=int(raw.get("last_update_index", -1)),
        trend=float(raw.get("trend", 0.0)),
        total_gain=float(raw.get("total_gain", 0.0)),
        total_decay=float(raw.get("total_decay", 0.0)),
        success_streak=int(raw.get("success_streak", 0)),
        mistake_streak=int(raw.get("mistake_streak", 0)),
        exposure_count=int(raw.get("exposure_count", 0)),
        history=[float(v) for v in (raw.get("history") or [])],
        evidence=_evidence_from_dict(raw.get("evidence") if isinstance(raw.get("evidence"), dict) else None),
    )


def build_initial_confidence_state(level: str) -> ConfidenceState:
    objectives = {
        oid: ObjectiveConfidenceRecord(objective_id=oid, label=label, confidence=INITIAL_CONFIDENCE)
        for oid, label in level_objectives(level)
    }
    return ConfidenceState(level=level, objectives=objectives)


def load_confidence_state(raw: dict | None, *, level: str) -> ConfidenceState:
    state = build_initial_confidence_state(level)
    if not isinstance(raw, dict):
        return state

    level_blob = raw.get(level) if isinstance(raw.get(level), dict) else raw
    if not isinstance(level_blob, dict):
        return state

    state.lesson_index = int(level_blob.get("lesson_index", 0))
    obj_blob = level_blob.get("objectives") or {}
    if isinstance(obj_blob, dict):
        for oid, label in level_objectives(level):
            if oid in obj_blob and isinstance(obj_blob[oid], dict):
                state.objectives[oid] = _record_from_dict(oid, label, obj_blob[oid])
    return state


def serialize_confidence_state(state: ConfidenceState) -> dict[str, object]:
    return {
        state.level: {
            "lesson_index": state.lesson_index,
            "objectives": {oid: rec.to_dict() for oid, rec in state.objectives.items()},
        }
    }


async def load_student_confidence(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    level: str,
) -> ConfidenceState:
    profile = await get_language_student_profile(
        db, student_id=student_id, language_id=language_id
    )
    if not profile or not isinstance(profile.preferences_json, dict):
        return build_initial_confidence_state(level)
    raw = profile.preferences_json.get(CONFIDENCE_KEY)
    return load_confidence_state(raw if isinstance(raw, dict) else None, level=level)


async def save_student_confidence(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    state: ConfidenceState,
) -> None:
    profile = await get_or_create_language_student_profile(
        db, student_id=student_id, language_id=language_id
    )
    prefs = dict(profile.preferences_json or {})
    existing = prefs.get(CONFIDENCE_KEY)
    merged: dict[str, object] = dict(existing) if isinstance(existing, dict) else {}
    merged.update(serialize_confidence_state(state))
    prefs[CONFIDENCE_KEY] = merged
    profile.preferences_json = prefs
    flag_modified(profile, "preferences_json")


def extract_seen_context(state: ConfidenceState) -> tuple[set[str], set[str]]:
    """Best-effort — full context rebuilt from lesson history in simulation."""
    return set(), set()
