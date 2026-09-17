"""Canonical Speaking Evaluation Result (S7) — single source of truth."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_speaking_educational_analyzer.types import SpeakingEducationalFacts
from app.services.language_speaking_evaluator.evaluation_facts_types import (
    SPEAKING_EVALUATION_FACTS_VERSION,
    DimensionEvidenceStatus,
)
from app.services.language_speaking_evaluator.input_types import (
    SpeakingGoalContext,
    SpeakingOfficialCefrContext,
    SpeakingTaskContext,
)

SPEAKING_EVALUATION_RESULT_VERSION = "7.0.0"

# Additive JSONB homes (no migration in S7):
# - LanguageSpeakingConversationTurn.evaluation_json["engine_result"]
# - LanguageSpeakingProgress.ai_evaluation_json["engine_result"]


@dataclass(frozen=True, slots=True)
class DimensionFacts:
    """Educational facts for one rubric dimension."""

    dimension: str
    status: DimensionEvidenceStatus
    normalized_value: float | None
    confidence: float
    reason: str
    supporting_evidence_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    score: float
    weight: float
    passed: bool
    evidence_codes: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "dimension": self.dimension,
            "status": self.status.value,
            "normalized_value": round(self.normalized_value, 4) if self.normalized_value is not None else None,
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
            "supporting_evidence_ids": list(self.supporting_evidence_ids),
            "limitations": list(self.limitations),
            "score": round(self.score, 4),
            "weight": round(self.weight, 4),
            "passed": self.passed,
            "evidence_codes": list(self.evidence_codes),
            "errors": list(self.errors),
        }


@dataclass(frozen=True, slots=True)
class EvidenceSummaryFacts:
    """Evaluator-local evidence summary — no audio_frontend import."""

    availability: dict[str, bool]
    reliability: float
    provider_provenance: tuple[dict[str, object], ...]
    evidence_reference_ids: tuple[str, ...]
    processing_warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "availability": dict(sorted(self.availability.items())),
            "reliability": round(self.reliability, 4),
            "provider_provenance": list(self.provider_provenance),
            "evidence_reference_ids": list(self.evidence_reference_ids),
            "processing_warnings": list(self.processing_warnings),
        }


@dataclass(frozen=True, slots=True)
class ExplanationFacts:
    summary: str
    priority_issue: str
    improvements: tuple[str, ...]
    strengths: tuple[str, ...]
    focus_label: str

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": self.summary,
            "priority_issue": self.priority_issue,
            "improvements": list(self.improvements),
            "strengths": list(self.strengths),
            "focus_label": self.focus_label,
        }


@dataclass(frozen=True, slots=True)
class RevisionReadinessFacts:
    ready: bool
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {"ready": self.ready, "blockers": list(self.blockers)}


@dataclass(frozen=True, slots=True)
class CompletionEligibilityFacts:
    """Separate from revision readiness — semantic task gate enforced."""

    eligible: bool
    reason: str
    semantic_task_met: bool
    acoustic_only_boost_blocked: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "eligible": self.eligible,
            "reason": self.reason,
            "semantic_task_met": self.semantic_task_met,
            "acoustic_only_boost_blocked": self.acoustic_only_boost_blocked,
        }


@dataclass(frozen=True, slots=True)
class SpeakingCandidateSkillEvidence:
    """Bridge toward S2 — no mutation in S7."""

    skill_id: str
    source_dimension: str
    performance: float
    confidence: float
    evidence_dimensions: tuple[str, ...]
    context_id: str
    success: bool
    mistake_tags: tuple[str, ...] = ()
    target_skill: bool = False
    communicative_impact: float | None = None
    supporting_evidence_ids: tuple[str, ...] = ()
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "skill_id": self.skill_id,
            "source_dimension": self.source_dimension,
            "performance": round(self.performance, 4),
            "confidence": round(self.confidence, 4),
            "evidence_dimensions": list(self.evidence_dimensions),
            "context_id": self.context_id,
            "success": self.success,
            "mistake_tags": list(self.mistake_tags),
            "target_skill": self.target_skill,
            "communicative_impact": round(self.communicative_impact, 4) if self.communicative_impact is not None else None,
            "supporting_evidence_ids": list(self.supporting_evidence_ids),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class SpeakingEvaluationEngineResult:
    """Canonical evaluation output — downstream packages render only; never recompute."""

    evaluation_id: str
    student_id: int
    language_id: int
    session_id: str
    task_id: str
    attempt_id: str
    revision_number: int
    evaluated_at: str
    task_context: SpeakingTaskContext
    goal_context: SpeakingGoalContext
    official_cefr_context: SpeakingOfficialCefrContext
    evidence_summary: EvidenceSummaryFacts
    task_response: DimensionFacts
    topic_understanding: DimensionFacts
    pronunciation: DimensionFacts
    fluency_delivery: DimensionFacts
    grammar: DimensionFacts
    vocabulary: DimensionFacts
    coherence: DimensionFacts
    interaction: DimensionFacts
    goal_alignment: DimensionFacts
    cefr_validation: DimensionFacts
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    priority_issue: str
    revision_readiness: RevisionReadinessFacts
    completion_eligibility: CompletionEligibilityFacts
    comparison_with_previous_attempt: str
    educational_analysis: SpeakingEducationalFacts | None
    candidate_skill_evidence: tuple[SpeakingCandidateSkillEvidence, ...]
    explanation: ExplanationFacts
    provider_provenance: tuple[dict[str, object], ...]
    weak_skills: tuple[str, ...]
    strong_skills: tuple[str, ...]
    overall_readiness: float
    engine_version: str = SPEAKING_EVALUATION_RESULT_VERSION

    @property
    def ready_to_complete(self) -> bool:
        return self.revision_readiness.ready

    def to_persistence_dict(self) -> dict[str, object]:
        def _dims() -> dict[str, object]:
            return {
                "task_response": self.task_response.to_dict(),
                "topic_understanding": self.topic_understanding.to_dict(),
                "pronunciation": self.pronunciation.to_dict(),
                "fluency_delivery": self.fluency_delivery.to_dict(),
                "grammar": self.grammar.to_dict(),
                "vocabulary": self.vocabulary.to_dict(),
                "coherence": self.coherence.to_dict(),
                "interaction": self.interaction.to_dict(),
                "goal_alignment": self.goal_alignment.to_dict(),
                "cefr_validation": self.cefr_validation.to_dict(),
            }

        return {
            "evaluation_id": self.evaluation_id,
            "student_id": self.student_id,
            "language_id": self.language_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "attempt_id": self.attempt_id,
            "revision_number": self.revision_number,
            "evaluated_at": self.evaluated_at,
            "task_context": {
                "task_id": self.task_context.task_id,
                "task_type": self.task_context.task_type,
                "task_prompt": self.task_context.task_prompt,
                "task_instructions": self.task_context.task_instructions,
                "success_criteria": list(self.task_context.success_criteria),
                "target_skill_ids": list(self.task_context.target_skill_ids),
            },
            "goal_context": {
                "speaking_goal": self.goal_context.speaking_goal,
                "goal_label": self.goal_context.goal_label,
            },
            "official_cefr_context": {
                "official_cefr": self.official_cefr_context.official_cefr,
                "band_descriptor": self.official_cefr_context.band_descriptor,
            },
            "evidence_summary": self.evidence_summary.to_dict(),
            "dimensions": _dims(),
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "priority_issue": self.priority_issue,
            "revision_readiness": self.revision_readiness.to_dict(),
            "completion_eligibility": self.completion_eligibility.to_dict(),
            "comparison_with_previous_attempt": self.comparison_with_previous_attempt,
            "educational_analysis": self.educational_analysis.to_persistence_dict() if self.educational_analysis else None,
            "candidate_skill_evidence": [c.to_dict() for c in self.candidate_skill_evidence],
            "explanation": self.explanation.to_dict(),
            "provider_provenance": list(self.provider_provenance),
            "weak_skills": list(self.weak_skills),
            "strong_skills": list(self.strong_skills),
            "overall_readiness": round(self.overall_readiness, 4),
            "engine_version": self.engine_version,
            "evaluation_facts_version": SPEAKING_EVALUATION_FACTS_VERSION,
        }
