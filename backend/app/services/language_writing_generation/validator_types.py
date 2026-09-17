"""Lesson Validator types (W5) — validate normalized draft against blueprint."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

VALIDATOR_VERSION = "5.0.0"


class ValidationSeverity(StrEnum):
    error = "error"
    warning = "warning"


class ValidationIssueCode(StrEnum):
    missing_required_field = "missing_required_field"
    grammar_metadata_mismatch = "grammar_metadata_mismatch"
    vocabulary_metadata_mismatch = "vocabulary_metadata_mismatch"
    success_criteria_mismatch = "success_criteria_mismatch"
    expected_output_mismatch = "expected_output_mismatch"
    constraints_incomplete = "constraints_incomplete"
    word_limit_missing = "word_limit_missing"
    cefr_metadata_missing = "cefr_metadata_missing"
    output_schema_incomplete = "output_schema_incomplete"
    learning_outcomes_mismatch = "learning_outcomes_mismatch"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: ValidationIssueCode
    field: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.error


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Outcome of lesson validation against blueprint."""

    passed: bool
    issues: tuple[ValidationIssue, ...]
    validator_version: str = VALIDATOR_VERSION

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.error)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.warning)

    def to_audit_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [
                {
                    "code": i.code.value,
                    "field": i.field,
                    "message": i.message,
                    "severity": i.severity.value,
                }
                for i in self.issues
            ],
        }
