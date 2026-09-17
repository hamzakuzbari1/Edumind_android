"""JSONB storage for E2 lesson runtime memory (sibling of E1 index; never mutates package)."""

from __future__ import annotations

from typing import Any

from app.services.language_speaking_lesson_runtime.types import LessonRuntimeState

SPEAKING_LESSON_RUNTIME_KEY = "speaking_lesson_runtime"


def runtime_from_payload(payload: dict[str, Any] | None) -> LessonRuntimeState | None:
    if not isinstance(payload, dict):
        return None
    raw = payload.get(SPEAKING_LESSON_RUNTIME_KEY)
    if not isinstance(raw, dict):
        return None
    return LessonRuntimeState.from_dict(raw)


def merge_runtime_into_payload(
    payload: dict[str, Any] | None,
    state: LessonRuntimeState,
) -> dict[str, Any]:
    out = dict(payload) if isinstance(payload, dict) else {}
    out[SPEAKING_LESSON_RUNTIME_KEY] = state.to_dict()
    return out


def clear_runtime_from_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(payload) if isinstance(payload, dict) else {}
    out.pop(SPEAKING_LESSON_RUNTIME_KEY, None)
    return out
