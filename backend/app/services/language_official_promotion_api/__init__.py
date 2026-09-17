"""Listening Official Promotion API service layer (PR-3)."""

from app.services.language_official_promotion_api.service import (
    OfficialPromotionApiError,
    apply_listening_official_promotion_api,
)

__all__ = [
    "OfficialPromotionApiError",
    "apply_listening_official_promotion_api",
]
