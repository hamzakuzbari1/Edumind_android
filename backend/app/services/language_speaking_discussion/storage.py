"""JSONB storage for E3 discussion runtime memory."""

from __future__ import annotations

from typing import Any

from app.services.language_speaking_discussion.types import DiscussionRuntimeState

SPEAKING_DISCUSSION_RUNTIME_KEY = "speaking_discussion_runtime"


def discussion_from_payload(payload: dict[str, Any] | None) -> DiscussionRuntimeState | None:
    if not isinstance(payload, dict):
        return None
    raw = payload.get(SPEAKING_DISCUSSION_RUNTIME_KEY)
    if not isinstance(raw, dict):
        return None
    return DiscussionRuntimeState.from_dict(raw)


def merge_discussion_into_payload(
    payload: dict[str, Any] | None,
    state: DiscussionRuntimeState,
) -> dict[str, Any]:
    out = dict(payload) if isinstance(payload, dict) else {}
    out[SPEAKING_DISCUSSION_RUNTIME_KEY] = state.to_dict()
    return out
