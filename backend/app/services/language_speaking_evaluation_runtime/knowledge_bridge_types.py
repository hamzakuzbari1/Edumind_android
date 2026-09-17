"""S8 bridge result types — S7 evaluation facts → S2 observations (no secrets)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.services.language_speaking_knowledge_model.types import SpeakingSkillEvidenceObservation

LANGUAGE_SPEAKING_KNOWLEDGE_BRIDGE_VERSION = "8.0.0"


class SpeakingKnowledgeMutationStatus(StrEnum):
    """Outcome of S7→S2 bridge mutation attempt."""

    applied = "applied"
    no_observations = "no_observations"
    skipped_all = "skipped_all"
    mutation_failed = "mutation_failed"
    s7_unavailable = "s7_unavailable"
    # S19: SPA evidence is quarantined — never default-applied into S2 mastery.
    quarantined_promotion_assessment = "quarantined_promotion_assessment"


@dataclass(frozen=True, slots=True)
class SkippedCandidateEvidence:
    """Diagnostic for a candidate that was not converted to an observation."""

    skill_id: str
    source_dimension: str
    reason: str


@dataclass(frozen=True, slots=True)
class SpeakingKnowledgeMutationBridgeResult:
    """Canonical S8 bridge output — translation only, no re-evaluation."""

    bridge_version: str
    source_evaluation_version: str
    turn_reference: str
    observations: tuple[SpeakingSkillEvidenceObservation, ...] = ()
    applied_observation_ids: tuple[str, ...] = ()
    skipped_candidate_evidence: tuple[SkippedCandidateEvidence, ...] = ()
    unknown_skill_ids: tuple[str, ...] = ()
    unavailable_dimensions: tuple[SkippedCandidateEvidence, ...] = ()
    mutation_status: SpeakingKnowledgeMutationStatus = SpeakingKnowledgeMutationStatus.no_observations
    mutation_error_code: str = ""

    def bridge_diagnostics(self) -> dict[str, object]:
        """API-safe diagnostics — no raw provider payloads."""
        return {
            "bridge_version": self.bridge_version,
            "source_evaluation_version": self.source_evaluation_version,
            "turn_reference": self.turn_reference,
            "mutation_status": str(self.mutation_status.value),
            "mutation_error_code": self.mutation_error_code,
            "observation_count": len(self.observations),
            "applied_observation_ids": list(self.applied_observation_ids),
            "unknown_skill_ids": list(self.unknown_skill_ids),
            "skipped_count": len(self.skipped_candidate_evidence),
            "unavailable_count": len(self.unavailable_dimensions),
        }
