"""Hume EVI tool dispatch for live speaking context (S7.6)."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_speaking_coach.evi_serialization import serialize_live_context_for_evi
from app.services.language_speaking_coach.types import (
    STUDENT_SPEAKING_LIVE_CONTEXT_VERSION,
    StudentSpeakingLiveContext,
)

logger = logging.getLogger(__name__)

SPEAKING_LIVE_TOOL_ALLOWLIST: frozenset[str] = frozenset({"get_student_speaking_context"})
LIVE_CONTEXT_CACHE_TTL_SECONDS = 120


@dataclass
class _CacheEntry:
    context: StudentSpeakingLiveContext
    expires_at: float


class LiveContextCache:
    """In-memory session-scoped cache — no cross-student leakage."""

    def __init__(self, *, ttl_seconds: int = LIVE_CONTEXT_CACHE_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._entries: dict[tuple[int, int], _CacheEntry] = {}

    def get(self, *, student_id: int, language_id: int) -> StudentSpeakingLiveContext | None:
        key = (student_id, language_id)
        entry = self._entries.get(key)
        if entry is None:
            return None
        if time.monotonic() >= entry.expires_at:
            del self._entries[key]
            return None
        return entry.context

    def set(self, *, student_id: int, language_id: int, context: StudentSpeakingLiveContext) -> None:
        self._entries[(student_id, language_id)] = _CacheEntry(
            context=context,
            expires_at=time.monotonic() + self._ttl,
        )

    def invalidate(self, *, student_id: int, language_id: int) -> None:
        self._entries.pop((student_id, language_id), None)

    def clear(self) -> None:
        self._entries.clear()


_GLOBAL_LIVE_CONTEXT_CACHE = LiveContextCache()


def get_live_context_cache() -> LiveContextCache:
    return _GLOBAL_LIVE_CONTEXT_CACHE


def invalidate_live_context(*, student_id: int, language_id: int = 1) -> None:
    _GLOBAL_LIVE_CONTEXT_CACHE.invalidate(student_id=student_id, language_id=language_id)


def _limited_context(*, student_reference: str = "unknown") -> StudentSpeakingLiveContext:
    now = datetime.now(tz=timezone.utc).isoformat()
    return StudentSpeakingLiveContext(
        context_version=STUDENT_SPEAKING_LIVE_CONTEXT_VERSION,
        student_reference=student_reference,
        speaking_goal="general_english",
        learner_state="limited_context",
        unavailable_context=("context_lookup_failed",),
        conversation_guidance=(
            "Proceed with a warm, natural conversation; detailed learner context is temporarily limited.",
        ),
        generated_at=now,
    )


async def dispatch_evi_tool(
    db: AsyncSession,
    *,
    tool_name: str,
    tool_call_id: str,
    authenticated_student_id: int,
    language_id: int = 1,
    parameters: str = "",
    speaking_goal: str = "general_english",
    cache: LiveContextCache | None = None,
) -> dict[str, object]:
    """Execute allowlisted tool for authenticated student only."""
    _ = tool_call_id
    if tool_name not in SPEAKING_LIVE_TOOL_ALLOWLIST:
        raise ValueError(f"unknown_tool:{tool_name}")

    # Never trust student_id from Hume parameters.
    if parameters:
        try:
            parsed = json.loads(parameters)
            if isinstance(parsed, dict) and parsed.get("student_id") not in (None, "", authenticated_student_id):
                logger.warning(
                    "Ignoring tool parameters student_id override",
                    extra={"tool": tool_name, "authenticated_student_id": authenticated_student_id},
                )
        except json.JSONDecodeError:
            pass

    store = cache or _GLOBAL_LIVE_CONTEXT_CACHE
    context = store.get(student_id=authenticated_student_id, language_id=language_id)
    if context is None:
        try:
            from app.services.language_speaking_coach.live_context_loader import load_student_speaking_live_context

            context = await load_student_speaking_live_context(
                db,
                student_id=authenticated_student_id,
                language_id=language_id,
                speaking_goal=speaking_goal,
            )
            store.set(student_id=authenticated_student_id, language_id=language_id, context=context)
        except Exception:
            logger.exception(
                "Live context lookup failed",
                extra={"student_id": authenticated_student_id, "tool": tool_name},
            )
            from app.services.language_speaking_coach.live_context_loader import opaque_student_reference

            context = _limited_context(
                student_reference=opaque_student_reference(student_id=authenticated_student_id)
            )

    content = serialize_live_context_for_evi(context)
    try:
        from app.services.language_speaking_coach.session_context_loader import load_session_evi_overlay
        from app.services.language_speaking_coach.session_live_context import merge_session_into_live_context

        session_ctx = await load_session_evi_overlay(
            db,
            student_id=authenticated_student_id,
            language_id=language_id,
        )
        if session_ctx:
            content = merge_session_into_live_context(context, session_ctx)
    except Exception:
        logger.debug("Session EVI overlay unavailable — using base live context", exc_info=True)

    return {"tool_call_id": tool_call_id, "content": content, "tool_name": tool_name}


async def handle_evi_tool_call(
    provider: Any,
    db: AsyncSession,
    event: dict[str, object],
    *,
    student_id: int,
    language_id: int = 1,
    speaking_goal: str = "general_english",
    cache: LiveContextCache | None = None,
) -> dict[str, object]:
    """Backend real-path: receive tool_call, dispatch, send tool_response/error."""
    tool_name = str(event.get("name") or "")
    tool_call_id = str(event.get("tool_call_id") or "")
    parameters = str(event.get("parameters") or "")

    if not tool_call_id:
        raise ValueError("missing_tool_call_id")

    if tool_name not in SPEAKING_LIVE_TOOL_ALLOWLIST:
        await provider.send_tool_error(
            tool_call_id=tool_call_id,
            error=f"unknown_tool:{tool_name}",
            content="This tool is not available in EduSpark live speaking.",
        )
        return {"handled": False, "reason": "unknown_tool"}

    try:
        result = await dispatch_evi_tool(
            db,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            authenticated_student_id=student_id,
            language_id=language_id,
            parameters=parameters,
            speaking_goal=speaking_goal,
            cache=cache,
        )
        await provider.send_tool_response(
            tool_call_id=tool_call_id,
            content=str(result["content"]),
            tool_name=tool_name,
        )
        return {"handled": True, **result}
    except Exception as exc:
        logger.exception("EVI tool dispatch failed", extra={"tool": tool_name, "student_id": student_id})
        safe = serialize_live_context_for_evi(_limited_context())
        await provider.send_tool_error(
            tool_call_id=tool_call_id,
            error=str(exc)[:200],
            content=safe,
        )
        return {"handled": True, "error": str(exc), "content": safe}
