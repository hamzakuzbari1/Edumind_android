"""Speaking promotion readiness types (S17).

Never mutates official_speaking_cefr, learning_stage_speaking, or S2.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from app.services.language_speaking.enums import SpeakingLearningStage
from app.services.language_speaking_promotion_readiness.policy import (
    LANGUAGE_SPEAKING_PROMOTION_READINESS_VERSION,
    READINESS_POLICY_VERSION,
    READINESS_SCHEMA_VERSION,
)


class SpeakingReadinessStatus(StrEnum):
    """Score/status band before dual-gate unlock is finalized by stability."""

    blocked = "blocked"
    not_ready = "not_ready"
    almost_ready = "almost_ready"
    ready = "ready"
    promotion_available_candidate = "promotion_available_candidate"


class SpeakingUnlockState(StrEnum):
    """Soft SPA unlock state (S17). Hard SPA sessions are S18+."""

    locked = "locked"
    readiness_building = "readiness_building"
    ready_to_unlock = "ready_to_unlock"
    unlocked = "unlocked"


@dataclass(frozen=True, slots=True)
class SpeakingReadinessDimensionScore:
    code: str
    current: float
    required: float
    progress: float
    weight: float
    contribution: float
    passed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "current": round(self.current, 4),
            "required": round(self.required, 4),
            "progress": round(self.progress, 4),
            "weight": round(self.weight, 4),
            "contribution": round(self.contribution, 4),
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class SpeakingPromotionReadinessResult:
    """Deterministic promotion-readiness evaluation (never writes CEFR)."""

    schema_version: str
    policy_version: str
    official_cefr: str
    target_cefr: str | None
    current_stage: SpeakingLearningStage
    eligible_for_readiness: bool
    readiness_score: int
    status: SpeakingReadinessStatus
    hard_blockers: tuple[str, ...]
    advisory_signals: tuple[str, ...]
    unknown_signals: tuple[str, ...]
    dimensions: tuple[SpeakingReadinessDimensionScore, ...]
    source_stage_signal_fingerprint: str
    snapshot_fingerprint: str
    estimated_remaining: float
    hard_blockers_empty: bool
    score_meets_promotion_floor: bool
    stability_requirements_passed: bool
    spa_unlocked: bool
    unlock_state: SpeakingUnlockState
    strengths: tuple[str, ...]
    next_actions: tuple[str, ...]

    def to_internal_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "official_cefr": self.official_cefr,
            "target_cefr": self.target_cefr,
            "current_stage": int(self.current_stage),
            "eligible_for_readiness": self.eligible_for_readiness,
            "readiness_score": self.readiness_score,
            "status": self.status.value,
            "hard_blockers": list(self.hard_blockers),
            "advisory_signals": list(self.advisory_signals),
            "unknown_signals": list(self.unknown_signals),
            "dimensions": [d.to_dict() for d in self.dimensions],
            "source_stage_signal_fingerprint": self.source_stage_signal_fingerprint,
            "snapshot_fingerprint": self.snapshot_fingerprint,
            "estimated_remaining": self.estimated_remaining,
            "hard_blockers_empty": self.hard_blockers_empty,
            "score_meets_promotion_floor": self.score_meets_promotion_floor,
            "stability_requirements_passed": self.stability_requirements_passed,
            "spa_unlocked": self.spa_unlocked,
            "unlock_state": self.unlock_state.value,
            "strengths": list(self.strengths),
            "next_actions": list(self.next_actions),
        }

    def to_student_safe_dict(self) -> dict[str, object]:
        """Journey-safe projection — no thresholds, fingerprints, or raw ratios."""
        messages = {
            SpeakingUnlockState.locked: "Keep building speaking skills at your current level.",
            SpeakingUnlockState.readiness_building: (
                "You are at Advanced — keep practicing for stable assessment readiness."
            ),
            SpeakingUnlockState.ready_to_unlock: (
                "You are close — a few more consistent sessions will unlock the next-level assessment."
            ),
            SpeakingUnlockState.unlocked: (
                "You are ready to attempt the next-level speaking assessment when it becomes available."
            ),
        }
        next_actions = {
            SpeakingUnlockState.locked: "Continue speaking practice missions.",
            SpeakingUnlockState.readiness_building: "Practice for broader, more stable speaking evidence.",
            SpeakingUnlockState.ready_to_unlock: "Complete a few more consistent speaking sessions.",
            SpeakingUnlockState.unlocked: "Start the next-level speaking assessment when offered.",
        }
        return {
            "status": self.status.value,
            "unlock_state": self.unlock_state.value,
            "spa_unlocked": self.spa_unlocked,
            "target_cefr": self.target_cefr,
            "message": messages[self.unlock_state],
            "next_action": next_actions[self.unlock_state],
            "eligible": self.eligible_for_readiness,
        }


def finalize_readiness_fingerprint(
    result: SpeakingPromotionReadinessResult,
) -> SpeakingPromotionReadinessResult:
    from app.services.language_speaking_promotion_readiness.fingerprint import (
        compute_readiness_fingerprint,
    )

    draft = replace(result, snapshot_fingerprint="")
    return replace(draft, snapshot_fingerprint=compute_readiness_fingerprint(draft))


__all__ = [
    "LANGUAGE_SPEAKING_PROMOTION_READINESS_VERSION",
    "SpeakingPromotionReadinessResult",
    "SpeakingReadinessDimensionScore",
    "SpeakingReadinessStatus",
    "SpeakingUnlockState",
    "finalize_readiness_fingerprint",
]
