"""Speaking promotion_stability (S17).

RESPONSIBILITY: Rolling readiness history / stability for dual-gate SPA unlock.
"""

from app.services.language_speaking_promotion_stability.engine import (
    evaluate_and_persist_speaking_promotion_stability,
    evaluate_speaking_promotion_stability,
)
from app.services.language_speaking_promotion_stability.policy import (
    DEFAULT_STABILITY_POLICY,
    LANGUAGE_SPEAKING_PROMOTION_STABILITY_VERSION,
    STABILITY_POLICY_VERSION,
    SpeakingStabilityPolicy,
)
from app.services.language_speaking_promotion_stability.types import (
    SpeakingPromotionStabilityResult,
    SpeakingReadinessHistoryEntry,
)

__all__ = [
    "DEFAULT_STABILITY_POLICY",
    "LANGUAGE_SPEAKING_PROMOTION_STABILITY_VERSION",
    "STABILITY_POLICY_VERSION",
    "SpeakingPromotionStabilityResult",
    "SpeakingReadinessHistoryEntry",
    "SpeakingStabilityPolicy",
    "evaluate_and_persist_speaking_promotion_stability",
    "evaluate_speaking_promotion_stability",
]
