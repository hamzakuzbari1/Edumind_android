"""Speaking promotion_test — SPA specification, constrained generation, frozen blueprints (S18).

RESPONSIBILITY: SPA blueprint specification, validation, bounded persistence, unlock reconcile (S18).
Does NOT score SPA, write official_speaking_cefr, apply S8 mastery, or claim interaction evidence
from recorded spontaneous production.
"""

from app.services.language_speaking_promotion_test.builder import build_spa_blueprint
from app.services.language_speaking_promotion_test.engine import create_speaking_promotion_assessment
from app.services.language_speaking_promotion_test.policy import (
    EVIDENCE_SOURCE_PROMOTION_ASSESSMENT,
    MAX_PERSISTED_BLUEPRINTS,
    SPA_POLICY_VERSION,
    SPA_REQUIRES_INTERACTION_EVIDENCE,
    SPA_SCHEMA_VERSION,
    SpaCapabilityKind,
    SpaExecutionMode,
    SpaSkillEvaluatorCompatibility,
    SpaTaskFamily,
    classify_skill_evaluator_compatibility,
    skill_requires_interactive_evaluation,
)
from app.services.language_speaking_promotion_test.specification import (
    SpaSpecificationError,
    build_speaking_promotion_assessment_specification,
)
from app.services.language_speaking_promotion_test.storage import (
    SPEAKING_PROMOTION_ASSESSMENTS_KEY,
    assert_bucket_bounded,
    assessments_bucket_from_payload,
    count_persisted_blueprints,
    get_active_blueprint,
    mark_active_terminal,
    merge_assessments_into_payload,
    persist_active_blueprint,
)
from app.services.language_speaking_promotion_test.types import (
    LANGUAGE_SPEAKING_PROMOTION_TEST_VERSION,
    SpaAssessmentCoverageGap,
    SpaBlueprintStatus,
    SpaCreateFailureCode,
    SpaCreateResult,
    SpaUnlockAuthority,
    SpeakingPromotionAssessmentBlueprint,
    SpeakingPromotionAssessmentSpecification,
    SpeakingPromotionAssessmentTask,
    SpeakingPromotionTestBundle,
)
from app.services.language_speaking_promotion_test.unlock import (
    reconcile_spa_unlock,
    resolve_next_speaking_cefr_local,
)
from app.services.language_speaking_promotion_test.validation import (
    validate_spa_blueprint,
    validate_spa_tasks_against_specification,
)

__all__ = [
    "EVIDENCE_SOURCE_PROMOTION_ASSESSMENT",
    "LANGUAGE_SPEAKING_PROMOTION_TEST_VERSION",
    "MAX_PERSISTED_BLUEPRINTS",
    "SPA_POLICY_VERSION",
    "SPA_REQUIRES_INTERACTION_EVIDENCE",
    "SPA_SCHEMA_VERSION",
    "SPEAKING_PROMOTION_ASSESSMENTS_KEY",
    "SpaAssessmentCoverageGap",
    "SpaBlueprintStatus",
    "SpaCapabilityKind",
    "SpaCreateFailureCode",
    "SpaCreateResult",
    "SpaExecutionMode",
    "SpaSkillEvaluatorCompatibility",
    "SpaSpecificationError",
    "SpaTaskFamily",
    "SpaUnlockAuthority",
    "SpeakingPromotionAssessmentBlueprint",
    "SpeakingPromotionAssessmentSpecification",
    "SpeakingPromotionAssessmentTask",
    "SpeakingPromotionTestBundle",
    "assert_bucket_bounded",
    "assessments_bucket_from_payload",
    "build_spa_blueprint",
    "build_speaking_promotion_assessment_specification",
    "classify_skill_evaluator_compatibility",
    "count_persisted_blueprints",
    "create_speaking_promotion_assessment",
    "get_active_blueprint",
    "mark_active_terminal",
    "merge_assessments_into_payload",
    "persist_active_blueprint",
    "reconcile_spa_unlock",
    "resolve_next_speaking_cefr_local",
    "skill_requires_interactive_evaluation",
    "validate_spa_blueprint",
    "validate_spa_tasks_against_specification",
]
