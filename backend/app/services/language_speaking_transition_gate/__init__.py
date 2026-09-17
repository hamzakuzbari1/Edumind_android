"""Speaking transition_gate (S16).

RESPONSIBILITY: Pure deterministic internal-stage transition authorization
within the current official_speaking_cefr. Never writes learning_stage_speaking,
official CEFR, promotion readiness, or S2. No AI.
"""

from app.services.language_speaking_transition_gate.fingerprint import (
    compute_decision_fingerprint,
    decision_fingerprint_payload,
)
from app.services.language_speaking_transition_gate.policy import (
    DEVELOPING_TO_ADVANCED,
    FOUNDATION_TO_DEVELOPING,
    GATE_POLICIES,
    SpeakingStageTransitionPolicy,
    ThresholdProvenance,
    ThresholdSourceKind,
    all_product_policy_default_fields,
    policy_for_transition,
)
from app.services.language_speaking_transition_gate.rules import evaluate_speaking_transition_gate
from app.services.language_speaking_transition_gate.types import (
    LANGUAGE_SPEAKING_TRANSITION_GATE_VERSION,
    TRANSITION_GATE_SCHEMA_VERSION,
    TRANSITION_POLICY_VERSION,
    ComparisonOperator,
    SpeakingStageRequirementResult,
    SpeakingStageTransitionDecision,
    SpeakingStageTransitionDecisionKind,
    SpeakingTransitionGateResult,
)

__all__ = [
    "LANGUAGE_SPEAKING_TRANSITION_GATE_VERSION",
    "TRANSITION_GATE_SCHEMA_VERSION",
    "TRANSITION_POLICY_VERSION",
    "ComparisonOperator",
    "DEVELOPING_TO_ADVANCED",
    "FOUNDATION_TO_DEVELOPING",
    "GATE_POLICIES",
    "SpeakingStageRequirementResult",
    "SpeakingStageTransitionDecision",
    "SpeakingStageTransitionDecisionKind",
    "SpeakingStageTransitionPolicy",
    "SpeakingTransitionGateResult",
    "ThresholdProvenance",
    "ThresholdSourceKind",
    "all_product_policy_default_fields",
    "compute_decision_fingerprint",
    "decision_fingerprint_payload",
    "evaluate_speaking_transition_gate",
    "policy_for_transition",
]
