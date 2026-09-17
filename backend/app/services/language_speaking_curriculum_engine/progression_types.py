"""Curriculum Progression Graph types — Curriculum Engine owned learning journey."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CaseVariant:
    """One Educational Case seed under a micro-skill node (same goal, different story)."""

    case_id: str
    title_hint: str
    scenario_type: str
    story_world: str
    character_hints: tuple[str, ...]
    case_category: str
    theme_key: str = ""
    emotional_theme: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title_hint": self.title_hint,
            "scenario_type": self.scenario_type,
            "story_world": self.story_world,
            "character_hints": list(self.character_hints),
            "case_category": self.case_category,
            "theme_key": self.theme_key,
            "emotional_theme": self.emotional_theme,
        }


@dataclass(frozen=True, slots=True)
class MicroSkillNode:
    """Graph node: teachable micro skill with multiple Educational Case variants."""

    node_id: str
    label: str
    cluster_id: str
    cluster_label: str
    domain_id: str
    domain_label: str
    parent_id: str | None
    children_ids: tuple[str, ...]
    prerequisite_ids: tuple[str, ...]
    recommended_next_ids: tuple[str, ...]
    difficulty: int
    cefr_min: str
    cefr_max: str
    estimated_mastery_enter: float
    estimated_mastery_advance: float
    micro_skills: tuple[str, ...]
    case_variants: tuple[CaseVariant, ...]
    required_grammar_hints: tuple[str, ...] = ()
    required_vocabulary_themes: tuple[str, ...] = ()
    linked_skill_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "cluster_id": self.cluster_id,
            "cluster_label": self.cluster_label,
            "domain_id": self.domain_id,
            "domain_label": self.domain_label,
            "parent_id": self.parent_id,
            "children_ids": list(self.children_ids),
            "prerequisite_ids": list(self.prerequisite_ids),
            "recommended_next_ids": list(self.recommended_next_ids),
            "difficulty": self.difficulty,
            "cefr_min": self.cefr_min,
            "cefr_max": self.cefr_max,
            "estimated_mastery_enter": self.estimated_mastery_enter,
            "estimated_mastery_advance": self.estimated_mastery_advance,
            "micro_skills": list(self.micro_skills),
            "case_variants": [c.to_dict() for c in self.case_variants],
            "required_grammar_hints": list(self.required_grammar_hints),
            "required_vocabulary_themes": list(self.required_vocabulary_themes),
            "linked_skill_ids": list(self.linked_skill_ids),
        }


@dataclass(frozen=True, slots=True)
class ProgressionDecision:
    """Resolved next Educational Case placement on the curriculum path."""

    action: str  # enter | repeat_new_case | advance
    node: MicroSkillNode
    case_variant: CaseVariant
    previous_node_id: str = ""
    prerequisites_met: bool = True
    estimated_mastery: float = 0.0
    path_index: int = 0
    path_length: int = 0
    reason: str = ""

    def to_constraints_dict(self) -> dict[str, Any]:
        n = self.node
        c = self.case_variant
        return {
            "cluster_id": n.cluster_id,
            "cluster_label": n.cluster_label,
            "domain_id": n.domain_id,
            "domain_label": n.domain_label,
            "micro_skill_id": n.node_id,
            "micro_skill_label": n.label,
            "micro_skills": list(n.micro_skills),
            "case_variant_id": c.case_id,
            "case_title_hint": c.title_hint,
            "action": self.action,
            "parent_id": n.parent_id,
            "children_ids": list(n.children_ids),
            "prerequisite_ids": list(n.prerequisite_ids),
            "recommended_next_ids": list(n.recommended_next_ids),
            "difficulty": n.difficulty,
            "estimated_mastery": self.estimated_mastery,
            "estimated_mastery_advance": n.estimated_mastery_advance,
            "prerequisites_met": self.prerequisites_met,
            "previous_node_id": self.previous_node_id,
            "path_index": self.path_index,
            "path_length": self.path_length,
            "cefr_min": n.cefr_min,
            "cefr_max": n.cefr_max,
            "theme_key": c.theme_key,
            "reason": self.reason,
        }


@dataclass(slots=True)
class ProgressionMasteryLedger:
    """Lightweight mastery / exposure by graph node (Curriculum-owned path state)."""

    schema_version: str = "1.0.0"
    current_node_id: str = ""
    node_mastery: dict[str, float] = field(default_factory=dict)
    node_exposure: dict[str, int] = field(default_factory=dict)
    used_case_ids: list[str] = field(default_factory=list)
    cluster_mastery: dict[str, float] = field(default_factory=dict)
    domain_mastery: dict[str, float] = field(default_factory=dict)
    completed_path: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "current_node_id": self.current_node_id,
            "node_mastery": dict(self.node_mastery),
            "node_exposure": dict(self.node_exposure),
            "used_case_ids": list(self.used_case_ids)[-60:],
            "cluster_mastery": dict(self.cluster_mastery),
            "domain_mastery": dict(self.domain_mastery),
            "completed_path": list(self.completed_path)[-40:],
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> ProgressionMasteryLedger:
        if not isinstance(raw, dict):
            return ProgressionMasteryLedger()
        return ProgressionMasteryLedger(
            schema_version=str(raw.get("schema_version") or "1.0.0"),
            current_node_id=str(raw.get("current_node_id") or ""),
            node_mastery={
                str(k): float(v)
                for k, v in dict(raw.get("node_mastery") or {}).items()
            },
            node_exposure={
                str(k): int(v)
                for k, v in dict(raw.get("node_exposure") or {}).items()
            },
            used_case_ids=[str(x) for x in (raw.get("used_case_ids") or []) if str(x).strip()],
            cluster_mastery={
                str(k): float(v)
                for k, v in dict(raw.get("cluster_mastery") or {}).items()
            },
            domain_mastery={
                str(k): float(v)
                for k, v in dict(raw.get("domain_mastery") or {}).items()
            },
            completed_path=[str(x) for x in (raw.get("completed_path") or []) if str(x).strip()],
        )
