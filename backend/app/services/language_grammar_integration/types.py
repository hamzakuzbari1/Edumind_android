"""Types for Grammar Integration (G3.1) — facade read models for Planner / skills.

Skills call resolve_targets for grammar_ids.
Skills emit Grammar Evidence; they never write mastery.
Planner consumes GrammarLearningSnapshot only — never engine internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.services.language_grammar.enums import (
    GrammarCEFRBand,
    GrammarEvidenceSourceSkill,
    GrammarMasteryState,
    GrammarReinforcementSkill,
    GrammarReviewMode,
    GrammarReviewPriority,
    GrammarReviewReason,
)
from app.services.language_grammar_mastery.types import PublicGrammarMasteryView
from app.services.language_grammar_progression.types import GrammarProgressionSnapshot

GRAMMAR_LEARNING_SNAPSHOT_VERSION = 1


@dataclass(frozen=True, slots=True)
class GrammarTopicPlanMeta:
    """Catalog fields Planner may use — copied into the learning snapshot."""

    grammar_id: str
    display_name: str
    cefr_band: GrammarCEFRBand
    learning_objectives: tuple[str, ...] = ()
    best_reinforcement_skills: tuple[GrammarReinforcementSkill, ...] = ()
    recommended_contexts: tuple[str, ...] = ()
    minimum_context_diversity: int = 2
    mastery_threshold: float = 80.0
    focus_note: str = ""
    evidence_min_observations: int = 3
    evidence_min_contexts: int = 2
    evidence_min_skills: int = 1


@dataclass(frozen=True, slots=True)
class GrammarReviewPlanItem:
    """Review queue row exposed to Planner (no Review engine types required)."""

    grammar_id: str
    due_at: str
    priority: GrammarReviewPriority
    reason: GrammarReviewReason
    recommended_review_mode: GrammarReviewMode
    review_due: bool = False
    urgency_score: float = 0.0


@dataclass(frozen=True, slots=True)
class GrammarMasteryPlanSummary:
    """Public mastery summary for Planner (overall only + state)."""

    grammar_id: str
    overall_mastery: float
    state: GrammarMasteryState
    evidence_count: int = 0
    distinct_context_count: int = 0
    last_seen_at: str | None = None


@dataclass(frozen=True, slots=True)
class GrammarLearningSnapshot:
    """Sole Planner input — assembled by GrammarIntegrationService."""

    student_id: int
    language_id: int
    overall_cefr: GrammarCEFRBand
    current_grammar_id: str | None
    next_grammar_id: str | None
    current_topic: GrammarTopicPlanMeta | None
    next_topic: GrammarTopicPlanMeta | None
    mastery_summaries: tuple[GrammarMasteryPlanSummary, ...] = ()
    review_queue: tuple[GrammarReviewPlanItem, ...] = ()
    catalog_version: str = ""
    catalog_schema_version: int = 1
    # Placeholder fatigue budget (minutes) — policy may use later; default stable.
    fatigue_budget_minutes: int = 45
    as_of: str = ""
    enabled: bool = True
    snapshot_version: int = GRAMMAR_LEARNING_SNAPSHOT_VERSION
    topic_index: dict[str, GrammarTopicPlanMeta] = field(default_factory=dict)

    def mastery_for(self, grammar_id: str) -> GrammarMasteryPlanSummary | None:
        for row in self.mastery_summaries:
            if row.grammar_id == grammar_id:
                return row
        return None

    def topic_meta(self, grammar_id: str) -> GrammarTopicPlanMeta | None:
        if self.current_topic and self.current_topic.grammar_id == grammar_id:
            return self.current_topic
        if self.next_topic and self.next_topic.grammar_id == grammar_id:
            return self.next_topic
        return self.topic_index.get(grammar_id)


@dataclass(frozen=True, slots=True)
class GrammarResolveTargetsRequest:
    """Skill planner request for grammar targets to inject into constraints."""

    student_id: int
    language_id: int
    source_skill: GrammarEvidenceSourceSkill
    max_targets: int = 2
    prefer_current: bool = True


@dataclass(frozen=True, slots=True)
class GrammarResolveTargetsResult:
    """Resolved grammar targets for skill constraints (read-only)."""

    grammar_ids: tuple[str, ...]
    anchor_cefr: GrammarCEFRBand
    progression: GrammarProgressionSnapshot | None = None
    public_mastery: tuple[PublicGrammarMasteryView, ...] = ()


@dataclass(frozen=True, slots=True)
class GrammarCompletedSyncResult:
    """Outcome of syncing Mastery mastered → Progression completed_ids."""

    synced_ids: tuple[str, ...] = ()
    already_completed: tuple[str, ...] = ()


class GrammarIntegrationPort(Protocol):
    """Port for skill planners — resolve only; no mastery writes."""

    def resolve_targets(self, request: GrammarResolveTargetsRequest) -> GrammarResolveTargetsResult:
        """Return grammar_ids for frozen skill constraints."""
        ...
