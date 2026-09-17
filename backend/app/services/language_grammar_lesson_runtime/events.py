"""Runtime event helpers (G3.2)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.language_grammar.enums import GrammarLessonStepKind
from app.services.language_grammar_lesson_runtime.types import (
    GrammarRuntimeEvent,
    GrammarRuntimeEventType,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_event(
    *,
    sequence: int,
    event_type: GrammarRuntimeEventType,
    lesson_id: str,
    at: str | None = None,
    step_id: str | None = None,
    step_kind: GrammarLessonStepKind | None = None,
    detail: str = "",
) -> GrammarRuntimeEvent:
    return GrammarRuntimeEvent(
        sequence=sequence,
        event_type=event_type,
        lesson_id=lesson_id,
        at=at or utc_now_iso(),
        step_id=step_id,
        step_kind=step_kind,
        detail=detail,
    )
