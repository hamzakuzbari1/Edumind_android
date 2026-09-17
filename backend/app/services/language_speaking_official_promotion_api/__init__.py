"""Public exports for speaking official promotion API (S20)."""

from app.services.language_speaking_official_promotion_api.service import (
    OfficialSpeakingPromotionApiError,
    apply_speaking_official_promotion_api,
)

__all__ = [
    "OfficialSpeakingPromotionApiError",
    "apply_speaking_official_promotion_api",
]
