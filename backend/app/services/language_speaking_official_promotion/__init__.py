"""Speaking official CEFR promotion (S20).

RESPONSIBILITY: Sole runtime writer of official_speaking_cefr after SPA PASS.
Consumes S19 assessment results. Does not score SPA, run readiness, or S7.
"""

from app.services.language_speaking_official_promotion.engine import (
    apply_speaking_official_promotion,
)
from app.services.language_speaking_official_promotion.ownership_guard import (
    AUTHORIZED_SPEAKING_CEFR_WRITERS,
    find_official_speaking_cefr_writers,
    verify_speaking_cefr_ownership,
)
from app.services.language_speaking_official_promotion.types import (
    SPEAKING_OFFICIAL_PROMOTION_VERSION,
    SPEAKING_OFFICIAL_PROMOTIONS_KEY,
    SpeakingOfficialPromotionResult,
)

__all__ = [
    "AUTHORIZED_SPEAKING_CEFR_WRITERS",
    "SPEAKING_OFFICIAL_PROMOTION_VERSION",
    "SPEAKING_OFFICIAL_PROMOTIONS_KEY",
    "SpeakingOfficialPromotionResult",
    "apply_speaking_official_promotion",
    "find_official_speaking_cefr_writers",
    "verify_speaking_cefr_ownership",
]
