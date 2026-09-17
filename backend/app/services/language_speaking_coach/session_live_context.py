"""Session-scoped EVI tutoring context overlay (S9)."""

from __future__ import annotations

import json

from app.services.language_speaking_coach.types import StudentSpeakingLiveContext

SESSION_EVI_MAX_CHARS = 2400


def merge_session_into_live_context(
    base: StudentSpeakingLiveContext,
    session_context: dict[str, object] | None,
) -> str:
    """Merge session-scoped tutoring frame into EVI payload — student-safe, no raw IDs."""
    payload: dict[str, object] = {
        "context_version": base.context_version,
        "student_reference": base.student_reference,
        "speaking_goal": base.speaking_goal,
        "learner_state": base.learner_state,
        "priority_skill_targets": [
            {"label": t.label, "skill_type": t.skill_type, "reason": t.reason}
            for t in base.priority_skill_targets
        ],
        "conversation_guidance": list(base.conversation_guidance),
        "recent_revision_needs": list(base.recent_revision_needs),
    }
    if session_context:
        payload["session_tutoring"] = {
            "session_goal": session_context.get("session_goal", ""),
            "target_skill_label": session_context.get("target_skill_label", ""),
            "communicative_scenario": session_context.get("communicative_scenario", ""),
            "encourage_behaviors": session_context.get("encourage_behaviors", []),
            "elicit_behaviors": session_context.get("elicit_behaviors", []),
            "retry_focus": session_context.get("retry_focus", ""),
            "conversation_constraints": session_context.get("conversation_constraints", []),
            "phase": session_context.get("phase", ""),
        }
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(text) > SESSION_EVI_MAX_CHARS:
        return text[:SESSION_EVI_MAX_CHARS]
    return text
