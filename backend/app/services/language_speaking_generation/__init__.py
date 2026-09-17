"""Speaking generation.

RESPONSIBILITY: Lesson/conversation/SPA wording generation (S10+/S18) — never promotion authority.
"""

from app.services.language_speaking_generation.promotion_assessment import (
    SPA_GENERATION_VERSION,
    SpeakingPromotionGeneratedTaskWording,
    SpeakingPromotionGenerationResult,
    SpeakingPromotionSlotGenerationConstraint,
    SpeakingPromotionTaskGenerationRequest,
    generate_spa_task_wording,
)
from app.services.language_speaking_generation.teaching_blocks import (
    GENERATION_FORBIDDEN_DECISIONS,
    TEACHING_GENERATION_VERSION,
    SpeakingTeachingBlockRequest,
    draft_teaching_block,
)
from app.services.language_speaking_generation.types import SpeakingGenerationRequest

__all__ = [
    "GENERATION_FORBIDDEN_DECISIONS",
    "SPA_GENERATION_VERSION",
    "TEACHING_GENERATION_VERSION",
    "SpeakingGenerationRequest",
    "SpeakingPromotionGeneratedTaskWording",
    "SpeakingPromotionGenerationResult",
    "SpeakingPromotionSlotGenerationConstraint",
    "SpeakingPromotionTaskGenerationRequest",
    "SpeakingTeachingBlockRequest",
    "draft_teaching_block",
    "generate_spa_task_wording",
]
