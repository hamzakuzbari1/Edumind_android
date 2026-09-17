"""Speaking Student Knowledge Model (S2).

RESPONSIBILITY: Per-skill mastery persistence, observation validation, and
deterministic mastery updates. Does NOT write official CEFR, learning stage,
or promotion readiness decisions.
"""

from app.services.language_speaking_knowledge_model.compatibility import (
    CompatibilityReport,
    get_or_create_skill_state,
    reconcile_model_with_graph,
)
from app.services.language_speaking_knowledge_model.engine import (
    apply_observation,
    apply_observations_batch,
    evaluate_mastery_requirements,
    refresh_retention_for_model,
)
from app.services.language_speaking_knowledge_model.json_mutation import mutate_speaking_knowledge_model
from app.services.language_speaking_knowledge_model.observation_validation import (
    evidence_coverage_for_state,
    validate_observation,
)
from app.services.language_speaking_knowledge_model.storage import (
    KNOWLEDGE_MODEL_KEY,
    SPEAKING_BUCKET_KEY,
    empty_knowledge_model,
    knowledge_model_from_dict,
    knowledge_model_from_speaking_bucket,
    knowledge_model_to_dict,
    merge_knowledge_model_into_speaking_bucket,
    speaking_bucket_from_payload,
)
from app.services.language_speaking_knowledge_model.types import (
    KNOWLEDGE_MODEL_SCHEMA_VERSION,
    OBSERVATION_HISTORY_CAP,
    OBSERVATION_INDEX_CAP,
    EvidenceCoverage,
    MasteryRequirementEvaluation,
    MistakePatternSummary,
    ObservationApplyResult,
    ObservationSourceType,
    SpeakingSkillEvidenceObservation,
    SpeakingSkillStatus,
    StudentSpeakingKnowledgeModel,
    StudentSpeakingSkillState,
)

__all__ = [
    "CompatibilityReport",
    "EvidenceCoverage",
    "KNOWLEDGE_MODEL_KEY",
    "KNOWLEDGE_MODEL_SCHEMA_VERSION",
    "MasteryRequirementEvaluation",
    "MistakePatternSummary",
    "OBSERVATION_HISTORY_CAP",
    "OBSERVATION_INDEX_CAP",
    "ObservationApplyResult",
    "ObservationSourceType",
    "SPEAKING_BUCKET_KEY",
    "SpeakingSkillEvidenceObservation",
    "SpeakingSkillStatus",
    "StudentSpeakingKnowledgeModel",
    "StudentSpeakingSkillState",
    "apply_observation",
    "apply_observations_batch",
    "empty_knowledge_model",
    "evaluate_mastery_requirements",
    "evidence_coverage_for_state",
    "get_or_create_skill_state",
    "knowledge_model_from_dict",
    "knowledge_model_from_speaking_bucket",
    "knowledge_model_to_dict",
    "merge_knowledge_model_into_speaking_bucket",
    "mutate_speaking_knowledge_model",
    "reconcile_model_with_graph",
    "refresh_retention_for_model",
    "speaking_bucket_from_payload",
    "validate_observation",
]
