"""Types for language_speaking_coach — live context + guidance (S7.6)."""

from __future__ import annotations

from dataclasses import dataclass, field

LANGUAGE_SPEAKING_COACH_VERSION = "0.2.0"
STUDENT_SPEAKING_LIVE_CONTEXT_VERSION = "7.6.0"


@dataclass(frozen=True, slots=True)
class SpeakingCoachGuidance:
    """Placeholder contract — render-only coach guidance (future phases)."""

    stub: bool = True
    version: str = LANGUAGE_SPEAKING_COACH_VERSION


@dataclass(frozen=True, slots=True)
class PrioritySkillTarget:
    """Compact priority target for live EVI grounding."""

    skill_id: str
    label: str
    skill_type: str
    reason: str


@dataclass(frozen=True, slots=True)
class StudentSpeakingLiveContext:
    """Read-only pedagogical context for Hume EVI Alex — never mutates S2/S7."""

    context_version: str
    student_reference: str
    speaking_goal: str
    learner_state: str
    priority_skill_targets: tuple[PrioritySkillTarget, ...] = ()
    recurring_mistake_patterns: tuple[str, ...] = ()
    retention_review_targets: tuple[str, ...] = ()
    recent_strengths: tuple[str, ...] = ()
    recent_revision_needs: tuple[str, ...] = ()
    conversation_guidance: tuple[str, ...] = ()
    unavailable_context: tuple[str, ...] = ()
    generated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "context_version": self.context_version,
            "student_reference": self.student_reference,
            "speaking_goal": self.speaking_goal,
            "learner_state": self.learner_state,
            "priority_skill_targets": [
                {
                    "skill_id": t.skill_id,
                    "label": t.label,
                    "skill_type": t.skill_type,
                    "reason": t.reason,
                }
                for t in self.priority_skill_targets
            ],
            "recurring_mistake_patterns": list(self.recurring_mistake_patterns),
            "retention_review_targets": list(self.retention_review_targets),
            "recent_strengths": list(self.recent_strengths),
            "recent_revision_needs": list(self.recent_revision_needs),
            "conversation_guidance": list(self.conversation_guidance),
            "unavailable_context": list(self.unavailable_context),
            "generated_at": self.generated_at,
        }
