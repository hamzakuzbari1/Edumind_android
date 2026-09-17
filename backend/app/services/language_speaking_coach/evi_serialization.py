"""Compact EVI serialization for StudentSpeakingLiveContext (S7.6)."""

from __future__ import annotations

import json

from app.services.language_speaking_coach.types import StudentSpeakingLiveContext

EVI_CONTEXT_MAX_CHARS = 2000


def serialize_live_context_for_evi(context: StudentSpeakingLiveContext) -> str:
    """Serialize to compact JSON string for Hume tool_response.content."""
    payload: dict[str, object] = {
        "context_version": context.context_version,
        "student_reference": context.student_reference,
        "speaking_goal": context.speaking_goal,
        "learner_state": context.learner_state,
        "priority_skill_targets": [
            {"label": t.label, "skill_type": t.skill_type, "reason": t.reason}
            for t in context.priority_skill_targets
        ],
        "recurring_mistake_patterns": list(context.recurring_mistake_patterns),
        "retention_review_targets": list(context.retention_review_targets),
        "recent_strengths": list(context.recent_strengths),
        "recent_revision_needs": list(context.recent_revision_needs),
        "conversation_guidance": list(context.conversation_guidance),
        "unavailable_context": list(context.unavailable_context),
    }
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(text) <= EVI_CONTEXT_MAX_CHARS:
        return text

    trimmed = dict(payload)
    for key in ("recent_strengths", "retention_review_targets", "recurring_mistake_patterns"):
        items = trimmed.get(key)
        if isinstance(items, list) and len(items) > 2:
            trimmed[key] = items[:2]
    text = json.dumps(trimmed, ensure_ascii=False, separators=(",", ":"))
    if len(text) <= EVI_CONTEXT_MAX_CHARS:
        return text

    trimmed["priority_skill_targets"] = trimmed.get("priority_skill_targets", [])[:2]
    trimmed["recent_revision_needs"] = trimmed.get("recent_revision_needs", [])[:2]
    trimmed["conversation_guidance"] = trimmed.get("conversation_guidance", [])[:3]
    text = json.dumps(trimmed, ensure_ascii=False, separators=(",", ":"))
    return text[:EVI_CONTEXT_MAX_CHARS]
