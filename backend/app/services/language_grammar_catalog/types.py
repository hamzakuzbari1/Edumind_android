"""Grammar Catalog types (G1) — sole authority for GrammarTopic definitions + DAG."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_grammar.enums import GrammarCEFRBand, GrammarReinforcementSkill

GRAMMAR_CATALOG_SCHEMA_VERSION = 1
GRAMMAR_CATALOG_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class GrammarEvidenceRequirements:
    """Catalog-owned gates before a topic may reach mastered (consumed by Mastery in G1+)."""

    min_observations: int = 3
    min_distinct_contexts: int = 2
    min_skills_covered: int = 1


@dataclass(frozen=True, slots=True)
class GrammarTopic:
    """Canonical catalog entry — single source of truth for a grammar topic."""

    grammar_id: str
    display_name: str
    cefr_band: GrammarCEFRBand
    introduction_order: int
    prerequisite_ids: tuple[str, ...] = ()
    # Forward edges (typically derived from reverse of prerequisites).
    future_topic_ids: tuple[str, ...] = ()
    learning_objectives: tuple[str, ...] = ()
    demonstration_patterns: tuple[str, ...] = ()
    example_sentences: tuple[str, ...] = ()
    common_errors: tuple[str, ...] = ()
    # Ordered preferred reinforcement skills for Grammar-session Blueprint.steps.
    best_reinforcement_skills: tuple[GrammarReinforcementSkill, ...] = ()
    recommended_contexts: tuple[str, ...] = ()
    minimum_context_diversity: int = 2
    evidence_requirements: GrammarEvidenceRequirements = field(
        default_factory=GrammarEvidenceRequirements
    )
    # Overall mastery score (0–100) recommended before state → mastered.
    mastery_threshold: float = 80.0
    # Higher = schedule review sooner / prefer in review queues (1–5).
    review_priority: int = 3
    review_half_life_days: float = 14.0
    focus_note: str = ""
    # Product/UI index only (e.g. G001). Never a persistent PK — grammar_id stays gram_*.
    display_code: str = ""
    estimated_duration_minutes: int = 25
    difficulty: str = "guided"
    teaching_notes: str = ""

    @property
    def label(self) -> str:
        """Backward-compatible alias for display_name."""
        return self.display_name

    @property
    def demonstration_forms(self) -> tuple[str, ...]:
        """Backward-compatible alias for demonstration_patterns."""
        return self.demonstration_patterns


@dataclass(frozen=True, slots=True)
class GrammarCatalogSnapshot:
    """Immutable catalog view for consumers (Progression/Planner later)."""

    version: str
    schema_version: int
    language_code: str
    topics: tuple[GrammarTopic, ...] = ()

    def topic_by_id(self, grammar_id: str) -> GrammarTopic | None:
        for topic in self.topics:
            if topic.grammar_id == grammar_id:
                return topic
        return None

    def topic_ids(self) -> frozenset[str]:
        return frozenset(t.grammar_id for t in self.topics)

    def topics_for_band(self, band: GrammarCEFRBand) -> tuple[GrammarTopic, ...]:
        return tuple(t for t in self.topics if t.cefr_band is band)

    def topics_up_to_band(self, band: GrammarCEFRBand) -> tuple[GrammarTopic, ...]:
        from app.services.language_grammar_catalog.cefr_order import cefr_rank

        limit = cefr_rank(band)
        return tuple(t for t in self.topics if cefr_rank(t.cefr_band) <= limit)
