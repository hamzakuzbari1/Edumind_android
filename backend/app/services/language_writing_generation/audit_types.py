"""Generation Audit types (W5) — persist generation metadata for traceability."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

GENERATION_AUDIT_VERSION = "5.0.0"


class GenerationOutcome(StrEnum):
    """Final pipeline outcome classification."""

    success = "success"
    soft_failure = "soft_failure"
    hard_failure = "hard_failure"


@dataclass(frozen=True, slots=True)
class WritingGenerationAuditRecord:
    """Metadata persisted after generation — no student PII."""

    blueprint_version: str
    blueprint_schema_version: str
    blueprint_hash: str
    prompt_version: str
    generator_version: str
    llm_version: str
    generation_hash: str
    generation_duration_ms: int
    validation_passed: bool
    validation_error_count: int
    validation_warning_count: int
    repair_applied: bool
    repair_action_count: int
    outcome: GenerationOutcome
    normalizer_version: str
    validator_version: str
    repair_layer_version: str
    audit_version: str = GENERATION_AUDIT_VERSION

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "blueprint_version": self.blueprint_version,
            "blueprint_schema_version": self.blueprint_schema_version,
            "blueprint_hash": self.blueprint_hash,
            "prompt_version": self.prompt_version,
            "generator_version": self.generator_version,
            "llm_version": self.llm_version,
            "generation_hash": self.generation_hash,
            "generation_duration_ms": self.generation_duration_ms,
            "validation_result": {
                "passed": self.validation_passed,
                "error_count": self.validation_error_count,
                "warning_count": self.validation_warning_count,
            },
            "repair_result": {
                "applied": self.repair_applied,
                "action_count": self.repair_action_count,
            },
            "outcome": self.outcome.value,
            "normalizer_version": self.normalizer_version,
            "validator_version": self.validator_version,
            "repair_layer_version": self.repair_layer_version,
            "audit_version": self.audit_version,
        }
