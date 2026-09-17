"""Speaking official promotion types (S20).

Sole runtime writer of official_speaking_cefr (placement remains separately authorized).
"""

from __future__ import annotations

from dataclasses import dataclass

SPEAKING_OFFICIAL_PROMOTION_VERSION = "20.0.0"
SPEAKING_OFFICIAL_PROMOTIONS_KEY = "speaking_official_promotions"
MAX_PROMOTION_EVENTS = 50
MAX_PROMOTED_IDS = 100


@dataclass(frozen=True, slots=True)
class SpeakingOfficialPromotionResult:
    """Engine / API result — student-safe fields only on the wire."""

    success: bool
    old_cefr: str
    new_cefr: str
    reason: str
    assessment_id: str = ""
    attempt_id: str = ""
    promoted_at: str = ""
    already_promoted: bool = False
    ready_for_new_journey: bool = False

    def to_student_safe_dict(self) -> dict:
        return {
            "promotion_success": self.success,
            "old_cefr": self.old_cefr,
            "new_cefr": self.new_cefr,
            "summary": self.reason if self.success else "",
            "reason": None if self.success else self.reason,
            "assessment_id": self.assessment_id,
            "attempt_id": self.attempt_id,
            "promoted_at": self.promoted_at,
            "already_promoted": self.already_promoted,
            "ready_for_new_journey": self.ready_for_new_journey and self.success,
            "new_learning_stage": 1 if self.success else 0,
        }
