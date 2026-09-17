"""Speaking stage transition gate types (S16).

Pure authorization contract. Never writes learning_stage_speaking,
official_speaking_cefr, promotion readiness, or S2.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.services.language_speaking.enums import SpeakingLearningStage

LANGUAGE_SPEAKING_TRANSITION_GATE_VERSION = "16.0.0"
TRANSITION_GATE_SCHEMA_VERSION = "16.0.0"
TRANSITION_POLICY_VERSION = "16.0.0"


class SpeakingStageTransitionDecisionKind(StrEnum):
    stay = "stay"
    advance = "advance"


class ComparisonOperator(StrEnum):
    """Exact comparison semantics for requirement evaluation."""

    ge = ">="
    gt = ">"
    le = "<="
    lt = "<"
    eq = "=="
    ne = "!="
    in_set = "in"
    is_not_none = "is_not_none"
    is_none = "is_none"
    absent = "absent"  # NOT_APPLICABLE / skipped


@dataclass(frozen=True, slots=True)
class SpeakingStageRequirementResult:
    """One evaluated gate requirement with explicit operator semantics."""

    code: str
    passed: bool
    current: str
    required: str
    operator: ComparisonOperator
    applicability: str  # required | advisory | not_applicable | unknown

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "passed": self.passed,
            "current": self.current,
            "required": self.required,
            "operator": self.operator.value,
            "applicability": self.applicability,
        }


@dataclass(frozen=True, slots=True)
class SpeakingStageTransitionDecision:
    """Deterministic internal-stage transition authorization (S16)."""

    schema_version: str
    policy_version: str
    official_cefr: str
    current_stage: SpeakingLearningStage
    target_stage: SpeakingLearningStage | None
    decision: SpeakingStageTransitionDecisionKind
    authorized: bool
    signal_fingerprint: str
    requirements: tuple[SpeakingStageRequirementResult, ...]
    blocking_reasons: tuple[str, ...]
    advisory_reasons: tuple[str, ...]
    satisfied_requirements: tuple[str, ...]
    unknown_requirements: tuple[str, ...]
    decision_fingerprint: str

    def to_internal_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "official_cefr": self.official_cefr,
            "current_stage": int(self.current_stage),
            "current_stage_name": self.current_stage.name,
            "target_stage": None if self.target_stage is None else int(self.target_stage),
            "decision": self.decision.value,
            "authorized": self.authorized,
            "signal_fingerprint": self.signal_fingerprint,
            "requirements": [r.to_dict() for r in self.requirements],
            "blocking_reasons": list(self.blocking_reasons),
            "advisory_reasons": list(self.advisory_reasons),
            "satisfied_requirements": list(self.satisfied_requirements),
            "unknown_requirements": list(self.unknown_requirements),
            "decision_fingerprint": self.decision_fingerprint,
        }


# Legacy S0 stub name retained for import compatibility.
SpeakingTransitionGateResult = SpeakingStageTransitionDecision
