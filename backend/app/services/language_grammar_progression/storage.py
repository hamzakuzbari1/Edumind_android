"""Typed Grammar Progression storage under promotion_readiness_json['grammar']['progression']."""

from __future__ import annotations

from typing import Any

from app.services.language_grammar.id_canon import normalize_grammar_id
from app.services.language_grammar.ownership import GRAMMAR_JSONB_NAMESPACE
from app.services.language_grammar.types import GRAMMAR_STORAGE_PROGRESSION_KEY
from app.services.language_grammar_progression.types import (
    GRAMMAR_PROGRESSION_SCHEMA_VERSION,
    GrammarProgressionStudentState,
)


def grammar_root_from_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    return dict((payload or {}).get(GRAMMAR_JSONB_NAMESPACE) or {})


def progression_bucket_from_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    root = grammar_root_from_payload(payload)
    return dict(root.get(GRAMMAR_STORAGE_PROGRESSION_KEY) or {})


def merge_progression_into_payload(
    payload: dict[str, Any] | None,
    bucket: dict[str, Any],
) -> dict[str, Any]:
    """Write progression bucket without clobbering mastery/review/runtime siblings."""
    out = dict(payload or {})
    root = dict(out.get(GRAMMAR_JSONB_NAMESPACE) or {})
    root[GRAMMAR_STORAGE_PROGRESSION_KEY] = dict(bucket)
    out[GRAMMAR_JSONB_NAMESPACE] = root
    return out


def _read_completed_ids(raw: dict[str, Any]) -> frozenset[str]:
    """Prefer completed_ids; migrate legacy cleared_ids if present."""
    values = raw.get("completed_ids")
    if values is None:
        values = raw.get("cleared_ids") or []
    return frozenset(normalize_grammar_id(x) for x in values if str(x).strip())


def student_state_from_bucket(
    bucket: dict[str, Any] | None,
    *,
    student_id: int,
    language_id: int,
) -> GrammarProgressionStudentState:
    raw = dict(bucket or {})
    unlocked = frozenset(
        normalize_grammar_id(x) for x in (raw.get("unlocked_ids") or []) if str(x).strip()
    )
    current = raw.get("current_grammar_id")
    current_id = normalize_grammar_id(str(current)) if current else None
    return GrammarProgressionStudentState(
        student_id=student_id,
        language_id=language_id,
        completed_ids=_read_completed_ids(raw),
        unlocked_ids=unlocked,
        current_grammar_id=current_id or None,
        stretch_allowed=bool(raw.get("stretch_allowed", False)),
    )


def bucket_from_student_state(state: GrammarProgressionStudentState) -> dict[str, Any]:
    """Persist only durable inputs — never derived candidate/locked/future lists."""
    return {
        "schema_version": GRAMMAR_PROGRESSION_SCHEMA_VERSION,
        "completed_ids": sorted(state.completed_ids),
        "unlocked_ids": sorted(state.unlocked_ids),
        "current_grammar_id": state.current_grammar_id,
        "stretch_allowed": bool(state.stretch_allowed),
    }


def apply_snapshot_unlocks_to_state(
    state: GrammarProgressionStudentState,
    *,
    unlocked_ids: tuple[str, ...],
    current_grammar_id: str | None,
) -> GrammarProgressionStudentState:
    """Merge computed unlocks into persisted state (monotonic unlock growth)."""
    merged_unlocked = frozenset(state.unlocked_ids) | frozenset(unlocked_ids)
    return GrammarProgressionStudentState(
        student_id=state.student_id,
        language_id=state.language_id,
        completed_ids=state.completed_ids,
        unlocked_ids=merged_unlocked,
        current_grammar_id=current_grammar_id,
        stretch_allowed=state.stretch_allowed,
    )
