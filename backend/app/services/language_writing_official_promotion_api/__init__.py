"""Writing Official Promotion API orchestration."""

from app.services.language_writing_official_promotion_api.service import (
    OfficialWritingPromotionApiError,
    apply_writing_official_promotion_api,
)

__all__ = [
    "OfficialWritingPromotionApiError",
    "apply_writing_official_promotion_api",
]
