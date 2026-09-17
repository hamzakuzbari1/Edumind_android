"""Speaking promotion_readiness (S17).

RESPONSIBILITY: Deterministic promotion readiness scoring for Speaking.
Never promotes official CEFR. Never invents support dependence.
"""

from app.services.language_speaking_promotion_readiness.engine import (
    evaluate_and_persist_speaking_promotion_readiness,
)
from app.services.language_speaking_promotion_readiness.policy import (
    DEFAULT_READINESS_POLICY,
    LANGUAGE_SPEAKING_PROMOTION_READINESS_VERSION,
    READINESS_POLICY_VERSION,
    READINESS_SCHEMA_VERSION,
    SpeakingPromotionReadinessPolicy,
    ThresholdProvenance,
    ThresholdSourceKind,
)
from app.services.language_speaking_promotion_readiness.scoring import (
    apply_dual_gate_unlock,
    evaluate_speaking_promotion_readiness,
)
from app.services.language_speaking_promotion_readiness.target_cefr import (
    NextCefrResolutionError,
    resolve_next_speaking_cefr,
)
from app.services.language_speaking_promotion_readiness.types import (
    SpeakingPromotionReadinessResult,
    SpeakingReadinessDimensionScore,
    SpeakingReadinessStatus,
    SpeakingUnlockState,
)

__all__ = [
    "DEFAULT_READINESS_POLICY",
    "LANGUAGE_SPEAKING_PROMOTION_READINESS_VERSION",
    "NextCefrResolutionError",
    "READINESS_POLICY_VERSION",
    "READINESS_SCHEMA_VERSION",
    "SpeakingPromotionReadinessPolicy",
    "SpeakingPromotionReadinessResult",
    "SpeakingReadinessDimensionScore",
    "SpeakingReadinessStatus",
    "SpeakingUnlockState",
    "ThresholdProvenance",
    "ThresholdSourceKind",
    "apply_dual_gate_unlock",
    "evaluate_and_persist_speaking_promotion_readiness",
    "evaluate_speaking_promotion_readiness",
    "resolve_next_speaking_cefr",
]
