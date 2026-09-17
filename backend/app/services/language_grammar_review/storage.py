"""Typed Grammar Review storage under promotion_readiness_json['grammar']['review']."""

from __future__ import annotations

from typing import Any

from app.services.language_grammar.enums import GrammarReviewMode
from app.services.language_grammar.id_canon import normalize_grammar_id
from app.services.language_grammar.ownership import GRAMMAR_JSONB_NAMESPACE
from app.services.language_grammar.types import GRAMMAR_STORAGE_REVIEW_KEY
from app.services.language_grammar_review.types import (
    GRAMMAR_REVIEW_SCHEMA_VERSION,
    GrammarReviewHistoryEntry,
    GrammarReviewStudentState,
)


def review_bucket_from_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    root = dict((payload or {}).get(GRAMMAR_JSONB_NAMESPACE) or {})
    return dict(root.get(GRAMMAR_STORAGE_REVIEW_KEY) or {})


def merge_review_into_payload(
    payload: dict[str, Any] | None,
    bucket: dict[str, Any],
) -> dict[str, Any]:
    """Write review bucket without clobbering mastery/progression/runtime siblings."""
    out = dict(payload or {})
    root = dict(out.get(GRAMMAR_JSONB_NAMESPACE) or {})
    root[GRAMMAR_STORAGE_REVIEW_KEY] = dict(bucket)
    out[GRAMMAR_JSONB_NAMESPACE] = root
    return out


def _history_from_raw(raw: dict[str, Any]) -> GrammarReviewHistoryEntry:
    gid = normalize_grammar_id(str(raw.get("grammar_id") or ""))
    if not gid:
        raise ValueError("Broken review state: empty grammar_id in history")
    count = int(raw.get("review_count") or 0)
    if count < 0:
        raise ValueError(f"Broken review state: negative review_count for {gid}")
    mode_raw = raw.get("last_mode")
    mode: GrammarReviewMode | None = None
    if mode_raw is not None and str(mode_raw).strip():
        try:
            mode = GrammarReviewMode(str(mode_raw))
        except ValueError as exc:
            raise ValueError(f"Broken review state: invalid last_mode {mode_raw}") from exc
    return GrammarReviewHistoryEntry(
        grammar_id=gid,
        last_reviewed_at=raw.get("last_reviewed_at"),
        review_count=count,
        last_mode=mode,
    )


def student_state_from_bucket(
    bucket: dict[str, Any] | None,
    *,
    student_id: int,
    language_id: int,
) -> GrammarReviewStudentState:
    raw = dict(bucket or {})
    history_raw = raw.get("history") or []
    entries: list[GrammarReviewHistoryEntry] = []
    seen: set[str] = set()
    for item in history_raw:
        if not isinstance(item, dict):
            continue
        entry = _history_from_raw(dict(item))
        if entry.grammar_id in seen:
            raise ValueError(f"Broken review state: duplicate history for {entry.grammar_id}")
        seen.add(entry.grammar_id)
        entries.append(entry)
    entries.sort(key=lambda e: e.grammar_id)
    return GrammarReviewStudentState(
        student_id=student_id,
        language_id=language_id,
        history=tuple(entries),
        schema_version=int(raw.get("schema_version") or GRAMMAR_REVIEW_SCHEMA_VERSION),
    )


def bucket_from_student_state(state: GrammarReviewStudentState) -> dict[str, Any]:
    """Persist durable review history only — never derived queue rows."""
    history: list[dict[str, Any]] = []
    for entry in sorted(state.history, key=lambda e: e.grammar_id):
        history.append(
            {
                "grammar_id": entry.grammar_id,
                "last_reviewed_at": entry.last_reviewed_at,
                "review_count": int(entry.review_count),
                "last_mode": entry.last_mode.value if entry.last_mode else None,
            }
        )
    return {
        "schema_version": GRAMMAR_REVIEW_SCHEMA_VERSION,
        "history": history,
    }
