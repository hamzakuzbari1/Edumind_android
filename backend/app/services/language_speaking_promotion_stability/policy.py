"""Speaking promotion stability policy (S17).

PRODUCT POLICY DEFAULT / LISTENING_ALIGNED_DEFAULT thresholds for rolling history.
One lucky session must never unlock SPA eligibility alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

LANGUAGE_SPEAKING_PROMOTION_STABILITY_VERSION = "17.0.0"
STABILITY_POLICY_VERSION = "17.0.0"


class StabilityThresholdSourceKind(StrEnum):
    product_policy_default = "PRODUCT_POLICY_DEFAULT"
    listening_aligned_default = "LISTENING_ALIGNED_DEFAULT"


@dataclass(frozen=True, slots=True)
class StabilityThresholdProvenance:
    policy_field: str
    value: str
    source_kind: StabilityThresholdSourceKind
    note: str

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_field": self.policy_field,
            "value": self.value,
            "source_kind": self.source_kind.value,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class SpeakingStabilityPolicy:
    policy_version: str
    rolling_window: int
    max_history_entries: int
    min_history_for_pass: int
    min_consecutive_high_scores: int
    high_score_threshold: int  # must align with readiness promotion floor (90)
    min_rolling_average: float
    min_rolling_minimum: float
    single_snapshot_confidence_cap: float
    short_history_confidence_cap: float
    min_promotion_confidence: float
    provenance: tuple[StabilityThresholdProvenance, ...]


def _sp(field: str, value: str, kind: StabilityThresholdSourceKind, note: str) -> StabilityThresholdProvenance:
    return StabilityThresholdProvenance(policy_field=field, value=value, source_kind=kind, note=note)


_STAB_PROV: tuple[StabilityThresholdProvenance, ...] = (
    _sp("rolling_window", "10", StabilityThresholdSourceKind.listening_aligned_default, "Listening StabilityPolicy.rolling_window"),
    _sp("max_history_entries", "24", StabilityThresholdSourceKind.listening_aligned_default, "Listening max_history_entries"),
    _sp("min_history_for_pass", "3", StabilityThresholdSourceKind.product_policy_default, "Dual-gate: need multiple snapshots"),
    _sp("min_consecutive_high_scores", "3", StabilityThresholdSourceKind.product_policy_default, "Consecutive >=90 scores"),
    _sp("high_score_threshold", "90", StabilityThresholdSourceKind.product_policy_default, "Matches readiness promotion_available_score"),
    _sp("min_rolling_average", "85.0", StabilityThresholdSourceKind.product_policy_default, "Slightly below Listening 90 for early speaking evidence volume"),
    _sp("min_rolling_minimum", "80.0", StabilityThresholdSourceKind.product_policy_default, "Aligned near Listening 85, relaxed for speaking"),
    _sp("single_snapshot_confidence_cap", "55.0", StabilityThresholdSourceKind.listening_aligned_default, "Listening single_lesson_confidence_cap"),
    _sp("short_history_confidence_cap", "72.0", StabilityThresholdSourceKind.listening_aligned_default, "Listening short_history_confidence_cap"),
    _sp("min_promotion_confidence", "75.0", StabilityThresholdSourceKind.product_policy_default, "Independent stability pass floor for dual-gate unlock"),
)


DEFAULT_STABILITY_POLICY = SpeakingStabilityPolicy(
    policy_version=STABILITY_POLICY_VERSION,
    rolling_window=10,
    max_history_entries=24,
    min_history_for_pass=3,
    min_consecutive_high_scores=3,
    high_score_threshold=90,
    min_rolling_average=85.0,
    min_rolling_minimum=80.0,
    single_snapshot_confidence_cap=55.0,
    short_history_confidence_cap=72.0,
    min_promotion_confidence=75.0,
    provenance=_STAB_PROV,
)
