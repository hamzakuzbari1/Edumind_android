"""Replaceable Overall Mastery derivation policies (G2.2 patch).

The Mastery Engine never hardcodes overall weighting. It delegates to the
active ``MasteryScoringPolicy``. Default production behavior is identical to
the original fixed-weight formula (0.30 / 0.35 / 0.20 / 0.15).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

# Production default weights (must sum to 1.0). Kept stable for BC.
OVERALL_WEIGHT_UNDERSTANDING = 0.30
OVERALL_WEIGHT_ACCURACY = 0.35
OVERALL_WEIGHT_FLUENCY = 0.20
OVERALL_WEIGHT_RETENTION = 0.15

DEFAULT_MASTERY_SCORING_POLICY_ID = "default_weighted_v1"


@dataclass(frozen=True, slots=True)
class MasteryDimensionInputs:
    """Inputs available to overall derivation.

    New pedagogical dimensions can be added here without changing the engine.
    Policies that do not use a field simply ignore it.
    """

    understanding: float
    accuracy: float
    fluency: float
    retention: float
    confidence: float = 0.0


@runtime_checkable
class MasteryScoringPolicy(Protocol):
    """Replaceable overall-mastery derivation strategy."""

    @property
    def policy_id(self) -> str: ...

    def derive_overall(self, dims: MasteryDimensionInputs) -> float:
        """Return Overall Mastery in [0, 100]. Must be deterministic."""
        ...


@dataclass(frozen=True, slots=True)
class DefaultWeightedMasteryScoringPolicy:
    """Canonical production policy — fixed weighted blend of four dimensions.

    Confidence is accepted for forward compatibility but unused so results
    match the pre-policy engine exactly.
    """

    policy_id: str = DEFAULT_MASTERY_SCORING_POLICY_ID
    weight_understanding: float = OVERALL_WEIGHT_UNDERSTANDING
    weight_accuracy: float = OVERALL_WEIGHT_ACCURACY
    weight_fluency: float = OVERALL_WEIGHT_FLUENCY
    weight_retention: float = OVERALL_WEIGHT_RETENTION

    def derive_overall(self, dims: MasteryDimensionInputs) -> float:
        overall = (
            self.weight_understanding * dims.understanding
            + self.weight_accuracy * dims.accuracy
            + self.weight_fluency * dims.fluency
            + self.weight_retention * dims.retention
        )
        return round(max(0.0, min(100.0, overall)), 4)


_DEFAULT_POLICY: MasteryScoringPolicy = DefaultWeightedMasteryScoringPolicy()
_active_policy: MasteryScoringPolicy = _DEFAULT_POLICY


def get_default_mastery_scoring_policy() -> MasteryScoringPolicy:
    return _DEFAULT_POLICY


def get_active_mastery_scoring_policy() -> MasteryScoringPolicy:
    return _active_policy


def set_active_mastery_scoring_policy(policy: MasteryScoringPolicy | None) -> MasteryScoringPolicy:
    """Install an active policy. Pass ``None`` to restore the production default."""
    global _active_policy
    _active_policy = _DEFAULT_POLICY if policy is None else policy
    return _active_policy


def derive_overall_via_policy(
    *,
    understanding: float,
    accuracy: float,
    fluency: float,
    retention: float,
    confidence: float = 0.0,
    policy: MasteryScoringPolicy | None = None,
) -> float:
    """Derive overall using ``policy`` or the active policy."""
    active = policy if policy is not None else _active_policy
    return active.derive_overall(
        MasteryDimensionInputs(
            understanding=understanding,
            accuracy=accuracy,
            fluency=fluency,
            retention=retention,
            confidence=confidence,
        )
    )
