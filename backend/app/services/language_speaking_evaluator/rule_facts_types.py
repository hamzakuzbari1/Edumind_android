"""Deterministic rule-engine facts before educational merge (S7)."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_speaking_evaluator.evaluation_result import (
    CompletionEligibilityFacts,
    DimensionFacts,
    EvidenceSummaryFacts,
    ExplanationFacts,
    RevisionReadinessFacts,
)

RULE_FACTS_VERSION = "7.0.0"


@dataclass(frozen=True, slots=True)
class TranscriptRuleFacts:
    has_transcript: bool
    word_count: int
    token_count: int
    is_empty_response: bool
    task_keyword_overlap_ratio: float
    task_keyword_hits: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PronunciationRuleFacts:
    available: bool
    substitution_count: int
    omission_count: int
    insertion_count: int
    issue_tags: tuple[str, ...]
    recurring_issue_tags: tuple[str, ...]
    coverage: float
    reliability: float
    affected_candidate_skill_ids: tuple[str, ...]
    processing_warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProsodyRuleFacts:
    available: bool
    pause_density: float | None
    long_pause_count: int
    pitch_variation: float | None
    energy_variation: float | None
    rhythm_regularity: float | None
    rate_proxy: float | None
    issue_tags: tuple[str, ...]
    stable_issue_tags: tuple[str, ...]
    reliability: float
    affected_candidate_skill_ids: tuple[str, ...]
    unavailable_families: tuple[str, ...] = ()
    processing_warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EvidenceQualityRuleFacts:
    transcript_available: bool
    pronunciation_available: bool
    prosody_available: bool
    overall_reliability: float
    partial_processing: bool
    provider_warnings: tuple[str, ...]
    missing_families: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SpeakingRuleEvaluationFacts:
    """Deterministic rule output — owns acoustic gates and dimension statuses."""

    evaluation_id: str
    session_id: str
    attempt_id: str
    revision_number: int
    transcript: TranscriptRuleFacts
    pronunciation: PronunciationRuleFacts
    prosody: ProsodyRuleFacts
    evidence_quality: EvidenceQualityRuleFacts
    evidence_summary: EvidenceSummaryFacts
    task_response: DimensionFacts
    topic_understanding: DimensionFacts
    pronunciation_dimension: DimensionFacts
    fluency_delivery: DimensionFacts
    grammar: DimensionFacts
    vocabulary: DimensionFacts
    coherence: DimensionFacts
    interaction: DimensionFacts
    goal_alignment: DimensionFacts
    cefr_validation: DimensionFacts
    revision_readiness: RevisionReadinessFacts
    completion_eligibility: CompletionEligibilityFacts
    explanation: ExplanationFacts
    weak_skills: tuple[str, ...]
    strong_skills: tuple[str, ...]
    overall_readiness: float
    rule_version: str = RULE_FACTS_VERSION
