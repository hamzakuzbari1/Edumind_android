"""Speaking promotion stability types (S17)."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_speaking_promotion_stability.policy import (
    LANGUAGE_SPEAKING_PROMOTION_STABILITY_VERSION,
    STABILITY_POLICY_VERSION,
)


@dataclass(frozen=True, slots=True)
class SpeakingReadinessHistoryEntry:
    signal_fingerprint: str
    readiness_score: int
    hard_blockers_empty: bool
    official_cefr: str
    target_cefr: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "signal_fingerprint": self.signal_fingerprint,
            "readiness_score": self.readiness_score,
            "hard_blockers_empty": self.hard_blockers_empty,
            "official_cefr": self.official_cefr,
            "target_cefr": self.target_cefr,
        }

    @staticmethod
    def from_dict(raw: dict[str, object]) -> SpeakingReadinessHistoryEntry:
        return SpeakingReadinessHistoryEntry(
            signal_fingerprint=str(raw.get("signal_fingerprint") or ""),
            readiness_score=int(raw.get("readiness_score") or 0),
            hard_blockers_empty=bool(raw.get("hard_blockers_empty")),
            official_cefr=str(raw.get("official_cefr") or ""),
            target_cefr=(None if raw.get("target_cefr") in (None, "") else str(raw.get("target_cefr"))),
        )


@dataclass(frozen=True, slots=True)
class SpeakingPromotionStabilityResult:
    schema_version: str
    policy_version: str
    history_length: int
    rolling_average: float
    rolling_minimum: float
    consecutive_high_scores: int
    promotion_confidence: float
    requirements_passed: bool
    failed_requirements: tuple[str, ...]
    last_scores: tuple[int, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "history_length": self.history_length,
            "rolling_average": self.rolling_average,
            "rolling_minimum": self.rolling_minimum,
            "consecutive_high_scores": self.consecutive_high_scores,
            "promotion_confidence": self.promotion_confidence,
            "requirements_passed": self.requirements_passed,
            "failed_requirements": list(self.failed_requirements),
            "last_scores": list(self.last_scores),
        }


LANGUAGE_SPEAKING_PROMOTION_STABILITY_SCHEMA = "17.0.0"

__all__ = [
    "LANGUAGE_SPEAKING_PROMOTION_STABILITY_SCHEMA",
    "LANGUAGE_SPEAKING_PROMOTION_STABILITY_VERSION",
    "STABILITY_POLICY_VERSION",
    "SpeakingPromotionStabilityResult",
    "SpeakingReadinessHistoryEntry",
]
