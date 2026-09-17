"""Types for language_speaking_diagnostic (S9) — deterministic target selection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

LANGUAGE_SPEAKING_DIAGNOSTIC_VERSION = "9.0.0"


class TargetSelectionReason(StrEnum):
    """Why the planner chose this speaking target — evidence-backed, not LLM."""

    sparse_evidence_safe_start = "sparse_evidence_safe_start"
    weak_mastery = "weak_mastery"
    at_risk_retention = "at_risk_retention"
    pronunciation_weakness = "pronunciation_weakness"
    delivery_weakness = "delivery_weakness"
    task_weakness = "task_weakness"
    reinforcement = "reinforcement"
    progression_next = "progression_next"
    remediation_follow_up = "remediation_follow_up"


@dataclass(frozen=True, slots=True)
class DiagnosticRecommendation:
    """Deterministic next-target recommendation from S1 graph + S2 state."""

    recommendation_id: str
    version: str
    primary_target_skill_id: str
    target_skill_ids: tuple[str, ...]
    selection_reason: TargetSelectionReason
    reason_detail: str
    evidence_basis: tuple[str, ...]
    blocked_skill_ids: tuple[str, ...]
    eligible_alternatives: tuple[str, ...]
    official_cefr_hint: str
    speaking_goal: str
    generated_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "recommendation_id": self.recommendation_id,
            "version": self.version,
            "primary_target_skill_id": self.primary_target_skill_id,
            "target_skill_ids": list(self.target_skill_ids),
            "selection_reason": self.selection_reason.value,
            "reason_detail": self.reason_detail,
            "evidence_basis": list(self.evidence_basis),
            "blocked_skill_ids": list(self.blocked_skill_ids),
            "eligible_alternatives": list(self.eligible_alternatives),
            "official_cefr_hint": self.official_cefr_hint,
            "speaking_goal": self.speaking_goal,
            "generated_at": self.generated_at,
        }
