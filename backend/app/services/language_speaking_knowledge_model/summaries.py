"""Derived summaries from StudentSpeakingKnowledgeModel (not persisted)."""

from __future__ import annotations

from app.services.language_speaking_knowledge_model.types import (
    SpeakingSkillStatus,
    StudentSpeakingKnowledgeModel,
)


def skills_by_status(
    model: StudentSpeakingKnowledgeModel,
    status: SpeakingSkillStatus,
) -> tuple[str, ...]:
    return tuple(
        sid
        for sid, st in model.skill_states.items()
        if st.current_status == status
    )


def mastered_skill_ids(model: StudentSpeakingKnowledgeModel) -> tuple[str, ...]:
    return skills_by_status(model, SpeakingSkillStatus.mastered)


def developing_skill_ids(model: StudentSpeakingKnowledgeModel) -> tuple[str, ...]:
    return tuple(
        sid
        for sid, st in model.skill_states.items()
        if st.current_status in (SpeakingSkillStatus.developing, SpeakingSkillStatus.observed)
    )


def at_risk_skill_ids(model: StudentSpeakingKnowledgeModel) -> tuple[str, ...]:
    return skills_by_status(model, SpeakingSkillStatus.at_risk)


def unseen_skill_ids(model: StudentSpeakingKnowledgeModel, *, catalog_ids: frozenset[str]) -> tuple[str, ...]:
    known = set(model.skill_states.keys())
    return tuple(sid for sid in sorted(catalog_ids) if sid not in known)
