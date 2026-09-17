"""Canonical Writing Evaluation Result — single source of truth for all educational decisions."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing_educational_analyzer.types import ClaudeEducationalFacts
from app.services.language_writing_evaluator.evaluation_facts_types import (
    CriterionStatus,
    DimensionResult,
    EVALUATION_FACTS_VERSION,
    SuccessCriterionStatus,
    WritingEvaluationFacts,
)
from app.services.language_writing_evaluator.types import (
    DimensionScore,
    EvaluationDimension,
    EvaluationIssue,
    EvaluationIssueCategory,
    EvaluationStrength,
    WritingEvaluationResult,
)
from app.services.language_writing_revision.comparison import RevisionComparisonResult

EVALUATION_RESULT_VERSION = "8.1.0"


@dataclass(frozen=True, slots=True)
class DimensionFacts:
    """Educational facts for one rubric dimension."""

    dimension: str
    score: float
    weight: float
    passed: bool
    evidence_codes: tuple[str, ...]
    errors: tuple[str, ...] = ()

    def to_dimension_result(self) -> DimensionResult:
        return DimensionResult(
            dimension=self.dimension,
            score=self.score,
            weight=self.weight,
            passed=self.passed,
            evidence_codes=self.evidence_codes,
        )


@dataclass(frozen=True, slots=True)
class CEFRValidationFacts:
    expected_band: str
    status: CriterionStatus
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RevisionReadinessFacts:
    ready: bool
    blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompletionFacts:
    """Completion eligibility — lesson `completed` is set by runtime when student confirms."""

    eligible: bool
    reason: str
    criteria_met_count: int
    criteria_total: int
    outcomes_met_count: int
    outcomes_total: int

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "eligible": self.eligible,
            "completed": self.eligible,
            "ready_to_complete": self.eligible,
            "reason": self.reason,
            "criteria_met_count": self.criteria_met_count,
            "criteria_total": self.criteria_total,
            "outcomes_met_count": self.outcomes_met_count,
            "outcomes_total": self.outcomes_total,
            "completion_version": EVALUATION_RESULT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ExplanationFacts:
    summary: str
    priority_issue: str
    improvements: tuple[str, ...]
    strengths: tuple[str, ...]
    focus_label: str


@dataclass(frozen=True, slots=True)
class WritingEvaluationEngineResult:
    """Canonical evaluation output — downstream packages render only; never recompute."""

    draft_id: str
    revision_number: int
    chain_node_id: str
    blueprint_version: str
    blueprint_hash: str
    generation_hash: str
    word_count: int
    meets_word_limit: bool
    grammar: DimensionFacts
    vocabulary: DimensionFacts
    organization: DimensionFacts
    task_completion: DimensionFacts
    goal_alignment: DimensionFacts
    cefr_validation: CEFRValidationFacts
    success_criteria: tuple[SuccessCriterionStatus, ...]
    learning_outcomes: tuple[SuccessCriterionStatus, ...]
    revision_readiness: RevisionReadinessFacts
    completion: CompletionFacts
    comparison: RevisionComparisonResult | None
    explanation: ExplanationFacts
    confidence: float
    weak_skills: tuple[str, ...]
    strong_skills: tuple[str, ...]
    critical_mistakes: tuple[str, ...]
    overall_readiness: float
    claude_analysis: ClaudeEducationalFacts | None = None
    engine_version: str = EVALUATION_RESULT_VERSION

    @property
    def ready_to_complete(self) -> bool:
        return self.revision_readiness.ready

    def to_coach_evaluation(self) -> WritingEvaluationResult:
        issues: list[EvaluationIssue] = []
        for dim in (self.grammar, self.vocabulary, self.organization):
            for err in dim.errors:
                cat = EvaluationIssueCategory.grammar
                if dim.dimension == "vocabulary":
                    cat = EvaluationIssueCategory.vocabulary
                elif dim.dimension == "organization":
                    cat = EvaluationIssueCategory.organization
                issues.append(
                    EvaluationIssue(
                        category=cat,
                        code=f"{dim.dimension}_error",
                        description_internal=err,
                        severity=0.85,
                    )
                )
        for mistake in self.critical_mistakes:
            issues.append(
                EvaluationIssue(
                    category=EvaluationIssueCategory.task,
                    code="critical_mistake",
                    description_internal=mistake,
                    severity=0.9,
                    matched_node_mistake=mistake,
                )
            )
        if not self.meets_word_limit and self.word_count < 1:
            pass
        elif self.task_completion.score < 0.5:
            issues.append(
                EvaluationIssue(
                    category=EvaluationIssueCategory.task,
                    code="task_incomplete",
                    description_internal="Task requirements not yet met",
                    severity=1.0 - self.task_completion.score,
                )
            )

        priority = issues[0] if issues else None
        if priority is None and self.explanation.priority_issue:
            priority = EvaluationIssue(
                category=EvaluationIssueCategory.grammar,
                code="priority",
                description_internal=self.explanation.priority_issue,
                severity=0.7,
            )

        strengths = tuple(
            EvaluationStrength(
                dimension=EvaluationDimension.grammar if s.startswith("grammar") else EvaluationDimension.organization,
                code=s,
                description_internal=s,
            )
            for s in self.strong_skills
        )

        dimension_scores = (
            DimensionScore(EvaluationDimension.grammar, self.grammar.score, self.grammar.evidence_codes),
            DimensionScore(EvaluationDimension.lexis, self.vocabulary.score, self.vocabulary.evidence_codes),
            DimensionScore(EvaluationDimension.organization, self.organization.score, self.organization.evidence_codes),
            DimensionScore(
                EvaluationDimension.task_achievement,
                self.task_completion.score,
                self.task_completion.evidence_codes,
            ),
            DimensionScore(EvaluationDimension.register, self.goal_alignment.score, self.goal_alignment.evidence_codes),
        )

        return WritingEvaluationResult(
            draft_id=self.draft_id,
            chain_node_id=self.chain_node_id,
            dimension_scores=dimension_scores,
            issues=tuple(issues),
            strengths=strengths,
            priority_issue=priority,
            task_completion_ratio=self.task_completion.score,
            word_count=self.word_count,
            meets_minimum_length=self.word_count >= 1 and self.meets_word_limit or self.word_count > 0,
            ready_to_complete_signal=self.revision_readiness.ready,
            evaluator_version=self.engine_version,
        )

    def to_evaluation_facts(self) -> WritingEvaluationFacts:
        """Backward-compatible facts view for persistence adapters."""
        return WritingEvaluationFacts(
            draft_id=self.draft_id,
            revision_number=self.revision_number,
            blueprint_version=self.blueprint_version,
            blueprint_hash=self.blueprint_hash,
            generation_hash=self.generation_hash,
            grammar_result=self.grammar.to_dimension_result(),
            vocabulary_result=self.vocabulary.to_dimension_result(),
            organization_result=self.organization.to_dimension_result(),
            task_completion_result=self.task_completion.to_dimension_result(),
            goal_alignment_result=self.goal_alignment.to_dimension_result(),
            word_count=self.word_count,
            meets_word_limit=self.meets_word_limit,
            critical_mistakes=self.critical_mistakes,
            strengths=self.strong_skills,
            weaknesses=self.weak_skills,
            success_criteria_status=self.success_criteria,
            learning_outcomes_status=self.learning_outcomes,
            overall_readiness=self.overall_readiness,
            ready_to_complete=self.revision_readiness.ready,
            evaluator_version=EVALUATION_FACTS_VERSION,
        )

    def to_persistence_dict(self) -> dict[str, object]:
        def _dim(d: DimensionFacts) -> dict[str, object]:
            return {
                "dimension": d.dimension,
                "score": round(d.score, 4),
                "weight": round(d.weight, 4),
                "passed": d.passed,
                "evidence_codes": list(d.evidence_codes),
                "errors": list(d.errors),
            }

        def _criteria(items: tuple[SuccessCriterionStatus, ...]) -> list[dict[str, object]]:
            return [{"label": i.label, "status": i.status.value, "code": i.code} for i in items]

        return {
            "draft_id": self.draft_id,
            "revision_number": self.revision_number,
            "chain_node_id": self.chain_node_id,
            "blueprint_version": self.blueprint_version,
            "blueprint_hash": self.blueprint_hash,
            "generation_hash": self.generation_hash,
            "word_count": self.word_count,
            "meets_word_limit": self.meets_word_limit,
            "grammar": _dim(self.grammar),
            "vocabulary": _dim(self.vocabulary),
            "organization": _dim(self.organization),
            "task_completion": _dim(self.task_completion),
            "goal_alignment": _dim(self.goal_alignment),
            "cefr_validation": {
                "expected_band": self.cefr_validation.expected_band,
                "status": self.cefr_validation.status.value,
                "notes": list(self.cefr_validation.notes),
            },
            "success_criteria": _criteria(self.success_criteria),
            "learning_outcomes": _criteria(self.learning_outcomes),
            "revision_readiness": {
                "ready": self.revision_readiness.ready,
                "blockers": list(self.revision_readiness.blockers),
            },
            "completion": self.completion.to_persistence_dict(),
            "comparison": self.comparison.to_persistence_dict() if self.comparison else None,
            "explanation": {
                "summary": self.explanation.summary,
                "priority_issue": self.explanation.priority_issue,
                "improvements": list(self.explanation.improvements),
                "strengths": list(self.explanation.strengths),
                "focus_label": self.explanation.focus_label,
            },
            "confidence": round(self.confidence, 4),
            "weak_skills": list(self.weak_skills),
            "strong_skills": list(self.strong_skills),
            "critical_mistakes": list(self.critical_mistakes),
            "overall_readiness": round(self.overall_readiness, 4),
            "engine_version": self.engine_version,
            "claude_analysis": self.claude_analysis.to_persistence_dict() if self.claude_analysis else None,
            # Legacy flat keys for older deserializers
            "grammar_result": _dim(self.grammar),
            "vocabulary_result": _dim(self.vocabulary),
            "organization_result": _dim(self.organization),
            "task_completion_result": _dim(self.task_completion),
            "goal_alignment_result": _dim(self.goal_alignment),
            "success_criteria_status": _criteria(self.success_criteria),
            "learning_outcomes_status": _criteria(self.learning_outcomes),
            "ready_to_complete": self.revision_readiness.ready,
            "evaluator_version": self.engine_version,
            "strengths": list(self.strong_skills),
            "weaknesses": list(self.weak_skills),
        }
