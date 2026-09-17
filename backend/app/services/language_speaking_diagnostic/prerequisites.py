"""Prerequisite guards for speaking skill eligibility (S9)."""

from __future__ import annotations

from app.services.language_speaking_curriculum.types import SpeakingSkillGraph, SpeakingSkillNode
from app.services.language_speaking_knowledge_model.types import StudentSpeakingKnowledgeModel

PREREQ_UNLOCK_MASTERY = 0.35
PREREQ_UNLOCK_EVIDENCE_MIN = 1


def prerequisite_state(
    node: SpeakingSkillNode,
    model: StudentSpeakingKnowledgeModel,
) -> tuple[bool, tuple[str, ...]]:
    """Return (satisfied, blocked_prerequisite_ids)."""
    blocked: list[str] = []
    for pid in node.prerequisite_skill_ids:
        state = model.skill_states.get(pid)
        if state is None:
            blocked.append(pid)
            continue
        if state.meets_mastery_requirements:
            continue
        if state.mastery >= PREREQ_UNLOCK_MASTERY and state.evidence_count >= PREREQ_UNLOCK_EVIDENCE_MIN:
            continue
        blocked.append(pid)
    return (len(blocked) == 0, tuple(blocked))


def eligible_skills(
    graph: SpeakingSkillGraph,
    model: StudentSpeakingKnowledgeModel,
) -> tuple[tuple[SpeakingSkillNode, tuple[str, ...]], ...]:
    """All graph nodes with (node, blocked_prereq_ids)."""
    out: list[tuple[SpeakingSkillNode, tuple[str, ...]]] = []
    for node in graph.nodes:
        ok, blocked = prerequisite_state(node, model)
        out.append((node, blocked if not ok else ()))
    return tuple(out)
