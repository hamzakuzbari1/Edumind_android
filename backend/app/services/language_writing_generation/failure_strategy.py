"""Failure strategy types (W5) — retry, repair, hard/soft failure policies."""

from __future__ import annotations

from dataclasses import dataclass

FAILURE_STRATEGY_VERSION = "5.0.0"

# Retry policy — future runtime only; documented here for architecture.
DEFAULT_MAX_LLM_RETRIES = 2
RETRY_ON_NORMALIZATION_FAILURE = True
RETRY_ON_HARD_VALIDATION_FAILURE = False
RETRY_BACKOFF_MS = (500, 1500)

# Repair policy — structural only.
REPAIR_ON_VALIDATION_WARNING = True
REPAIR_ON_VALIDATION_ERROR = True
REPAIR_MAX_PASSES = 1

# Hard failure — no lesson persisted.
HARD_FAILURE_TRIGGERS: frozenset[str] = frozenset(
    {
        "invalid_json",
        "not_object",
        "missing_required_field_after_repair",
        "grammar_metadata_mismatch_after_repair",
        "vocabulary_metadata_mismatch_after_repair",
        "expected_output_mismatch_after_repair",
        "max_llm_retries_exceeded",
    }
)

# Soft failure — lesson persisted with repair audit flag.
SOFT_FAILURE_TRIGGERS: frozenset[str] = frozenset(
    {
        "checklist_restored_from_blueprint",
        "tips_restored_from_mission",
        "learning_outcomes_restored_from_blueprint",
        "success_criteria_restored_from_blueprint",
        "constraints_restored_from_mission",
        "enum_casing_normalized",
        "empty_optional_array_filled",
    }
)


@dataclass(frozen=True, slots=True)
class FailureStrategyPolicy:
    """Documented failure handling policy — architecture contract."""

    max_llm_retries: int = DEFAULT_MAX_LLM_RETRIES
    retry_on_normalization_failure: bool = RETRY_ON_NORMALIZATION_FAILURE
    retry_on_hard_validation_failure: bool = RETRY_ON_HARD_VALIDATION_FAILURE
    repair_on_validation_warning: bool = REPAIR_ON_VALIDATION_WARNING
    repair_on_validation_error: bool = REPAIR_ON_VALIDATION_ERROR
    repair_max_passes: int = REPAIR_MAX_PASSES
    version: str = FAILURE_STRATEGY_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "max_llm_retries": self.max_llm_retries,
            "retry_on_normalization_failure": self.retry_on_normalization_failure,
            "retry_on_hard_validation_failure": self.retry_on_hard_validation_failure,
            "repair_on_validation_warning": self.repair_on_validation_warning,
            "repair_on_validation_error": self.repair_on_validation_error,
            "repair_max_passes": self.repair_max_passes,
            "hard_failure_triggers": sorted(HARD_FAILURE_TRIGGERS),
            "soft_failure_triggers": sorted(SOFT_FAILURE_TRIGGERS),
            "version": self.version,
        }


DEFAULT_FAILURE_STRATEGY = FailureStrategyPolicy()
