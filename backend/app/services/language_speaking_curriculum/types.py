"""Speaking Skill Dependency Graph types (S1).

Consumer map (future phases):
- skill_id, skill_type, prerequisites → S2 mastery keys, S8 diagnostic selection
- mastery_requirements → S2 Student Knowledge Model scoring gates
- evidence_requirements → S7 Evaluation Engine criterion mapping
- goal_relevance → S8 goal-weighted diagnostic, S9 Teaching Planner
- diagnostic_tags / remediation_tags → S8 trace-back, S12 Coach priority hints
- recommended_activity_types → S9 blueprint, S10 generation
- spaced_repetition_profile → S2 retention scheduling
- transfer_targets → S8 cross-skill remediation routing
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_speaking.enums import (
    OfficialSpeakingCEFR,
    SpeakingGoal,
    SpeakingSkillType,
    SpeakingTaskType,
)

SPEAKING_SKILL_GRAPH_VERSION = "1.0.0"
SPEAKING_SKILL_SCHEMA_VERSION = "1.0.0"
LANGUAGE_SPEAKING_CURRICULUM_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class SkillEvidenceRequirement:
    """What evidence dimensions can support mastery of this skill (S7 maps providers)."""

    evidence_codes: tuple[str, ...]
    minimum_dimensions: int = 1
    notes: str = ""


@dataclass(frozen=True, slots=True)
class SkillMasteryRequirement:
    """Catalog-defined mastery gates — S2 evaluates; never invented at runtime."""

    minimum_evidence_count: int
    stability_sessions: int = 2
    pronunciation_threshold: float | None = None
    communicative_success_threshold: float | None = None
    distinct_word_contexts: int | None = None
    minimum_interaction_turns: int | None = None
    response_relevance_threshold: float | None = None
    task_response_required: bool = False
    organization_required: bool = False
    fluency_required: bool = False
    grammar_vocabulary_required: bool = False
    repeated_successful_contexts: int | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class SpacedRepetitionProfile:
    """S2 retention scheduler input."""

    initial_interval_days: int
    ease_factor: float = 2.5
    max_interval_days: int = 90


@dataclass(frozen=True, slots=True)
class SpeakingSkillNode:
    """Canonical node in the Speaking Skill Dependency Graph."""

    skill_id: str
    skill_type: SpeakingSkillType
    label: str
    description: str
    cefr_min: OfficialSpeakingCEFR
    cefr_max: OfficialSpeakingCEFR
    prerequisite_skill_ids: tuple[str, ...]
    next_skill_ids: tuple[str, ...]
    related_skill_ids: tuple[str, ...]
    difficulty: int
    mastery_requirements: SkillMasteryRequirement
    evidence_requirements: SkillEvidenceRequirement
    recommended_activity_types: tuple[SpeakingTaskType, ...]
    spaced_repetition_profile: SpacedRepetitionProfile | None
    goal_relevance: tuple[SpeakingGoal, ...]
    speaking_functions: tuple[str, ...]
    task_relevance: tuple[str, ...]
    diagnostic_tags: tuple[str, ...]
    remediation_tags: tuple[str, ...]
    transfer_targets: tuple[str, ...]
    is_root: bool = False

    @property
    def flagship_area(self) -> str | None:
        for tag in self.diagnostic_tags:
            if tag.startswith("area:"):
                return tag[5:]
        return None


@dataclass(frozen=True, slots=True)
class SpeakingSkillGraph:
    """Immutable catalog of all speaking skills and prerequisite DAG."""

    version: str
    schema_version: str
    nodes: tuple[SpeakingSkillNode, ...]

    def node_by_id(self, skill_id: str) -> SpeakingSkillNode | None:
        for node in self.nodes:
            if node.skill_id == skill_id:
                return node
        return None

    def node_ids(self) -> frozenset[str]:
        return frozenset(n.skill_id for n in self.nodes)

    @property
    def roots(self) -> tuple[SpeakingSkillNode, ...]:
        return tuple(n for n in self.nodes if n.is_root or not n.prerequisite_skill_ids)
