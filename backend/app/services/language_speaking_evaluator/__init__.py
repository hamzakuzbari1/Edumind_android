"""Speaking canonical evaluation engine (S7).

RESPONSIBILITY: SpeakingEvaluationEngineResult and hybrid rule+Claude merge.
"""

from app.services.language_speaking_evaluator.candidate_skill_evidence import build_candidate_skill_evidence
from app.services.language_speaking_evaluator.evaluation_result import SpeakingCandidateSkillEvidence
from app.services.language_speaking_evaluator.engine import (
    EVALUATOR_RUNTIME_VERSION,
    HYBRID_ENGINE_VERSION,
    evaluate_speaking_turn,
    evaluate_speaking_turn_sync,
    new_evaluation_context,
)
from app.services.language_speaking_evaluator.evaluation_result import (
    SPEAKING_EVALUATION_RESULT_VERSION,
    CompletionEligibilityFacts,
    DimensionFacts,
    EvidenceSummaryFacts,
    ExplanationFacts,
    RevisionReadinessFacts,
    SpeakingEvaluationEngineResult,
)
from app.services.language_speaking_evaluator.facts_deserialize import evaluation_result_from_dict
from app.services.language_speaking_evaluator.hybrid_merge import HYBRID_ENGINE_VERSION as MERGE_VERSION, merge_speaking_evaluation
from app.services.language_speaking_evaluator.input_types import (
    SpeakingEvaluationContext,
    SpeakingEvaluationInput,
    SpeakingGoalContext,
    SpeakingOfficialCefrContext,
    SpeakingTaskContext,
)
from app.services.language_speaking_evaluator.rule_engine import RULE_ENGINE_VERSION, evaluate_speaking_evidence

__all__ = [
    "EVALUATOR_RUNTIME_VERSION",
    "HYBRID_ENGINE_VERSION",
    "MERGE_VERSION",
    "RULE_ENGINE_VERSION",
    "SPEAKING_EVALUATION_RESULT_VERSION",
    "CompletionEligibilityFacts",
    "DimensionFacts",
    "EvidenceSummaryFacts",
    "ExplanationFacts",
    "RevisionReadinessFacts",
    "SpeakingCandidateSkillEvidence",
    "SpeakingEvaluationContext",
    "SpeakingEvaluationEngineResult",
    "SpeakingEvaluationInput",
    "SpeakingGoalContext",
    "SpeakingOfficialCefrContext",
    "SpeakingTaskContext",
    "build_candidate_skill_evidence",
    "evaluate_speaking_evidence",
    "evaluate_speaking_turn",
    "evaluate_speaking_turn_sync",
    "evaluation_result_from_dict",
    "merge_speaking_evaluation",
    "new_evaluation_context",
]
