"""Canonical evaluation facts types (S7)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

SPEAKING_EVALUATION_FACTS_VERSION = "7.0.0"


class CriterionStatus(StrEnum):
    met = "met"
    partial = "partial"
    not_met = "not_met"
    attempted_inaccurately = "attempted_inaccurately"
    not_attempted = "not_attempted"


class DimensionEvidenceStatus(StrEnum):
    met = "met"
    partial = "partial"
    not_met = "not_met"
    insufficient_evidence = "insufficient_evidence"
    not_applicable = "not_applicable"


@dataclass(frozen=True, slots=True)
class DimensionResult:
    dimension: str
    score: float
    weight: float
    passed: bool
    evidence_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SuccessCriterionStatus:
    label: str
    status: CriterionStatus
    code: str = ""
