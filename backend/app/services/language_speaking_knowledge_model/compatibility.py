"""Graph version compatibility for persisted Speaking knowledge (S2)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_curriculum.types import SPEAKING_SKILL_GRAPH_VERSION
from app.services.language_speaking_knowledge_model.types import (
    StudentSpeakingKnowledgeModel,
    StudentSpeakingSkillState,
)


@dataclass
class CompatibilityReport:
    ok: bool = True
    graph_version_stored: str = ""
    graph_version_current: str = SPEAKING_SKILL_GRAPH_VERSION
    unknown_skill_ids: list[str] = field(default_factory=list)
    new_skill_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def reconcile_model_with_graph(model: StudentSpeakingKnowledgeModel) -> CompatibilityReport:
    """Align persisted model with current S1 graph without deleting student mastery."""
    report = CompatibilityReport(graph_version_stored=model.graph_version or "")
    catalog_ids = SPEAKING_SKILL_GRAPH.node_ids()

    for sid in sorted(model.skill_states.keys()):
        if sid not in catalog_ids:
            report.unknown_skill_ids.append(sid)
            deprecated = model.skill_states.pop(sid)
            model.deprecated_skill_states[sid] = deprecated
            report.notes.append(f"moved unknown skill_id to deprecated: {sid}")

    for sid in sorted(catalog_ids):
        if sid not in model.skill_states and sid not in model.deprecated_skill_states:
            report.new_skill_ids.append(sid)

    if report.unknown_skill_ids:
        report.notes.append("unknown persisted skills preserved under deprecated_skill_states")

    if model.graph_version and model.graph_version != SPEAKING_SKILL_GRAPH_VERSION:
        report.notes.append(
            f"graph version changed {model.graph_version} -> {SPEAKING_SKILL_GRAPH_VERSION}"
        )

    model.graph_version = SPEAKING_SKILL_GRAPH_VERSION
    model.compatibility_notes = list(dict.fromkeys(model.compatibility_notes + report.notes))
    return report


def get_or_create_skill_state(
    model: StudentSpeakingKnowledgeModel,
    skill_id: str,
) -> StudentSpeakingSkillState | None:
    if skill_id in model.skill_states:
        return model.skill_states[skill_id]
    if skill_id not in SPEAKING_SKILL_GRAPH.node_ids():
        return None
    state = StudentSpeakingSkillState(skill_id=skill_id)
    model.skill_states[skill_id] = state
    return state
