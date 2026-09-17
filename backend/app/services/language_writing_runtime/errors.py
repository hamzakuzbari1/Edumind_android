"""Structured runtime errors (W6) — no raw provider exceptions escape the runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class WritingRuntimeErrorCode(StrEnum):
    provider_unavailable = "provider_unavailable"
    provider_timeout = "provider_timeout"
    provider_rate_limit = "provider_rate_limit"
    provider_error = "provider_error"
    malformed_json = "malformed_json"
    validation_failure = "validation_failure"
    repair_failure = "repair_failure"
    repair_success = "repair_success"
    blueprint_assembly_failed = "blueprint_assembly_failed"
    persistence_failed = "persistence_failed"
    generation_gate_closed = "generation_gate_closed"


@dataclass(frozen=True, slots=True)
class WritingRuntimeError:
    """Structured error returned to callers — never wrap raw Anthropic exceptions."""

    code: WritingRuntimeErrorCode
    message: str
    retryable: bool = False
    provider_name: str = ""
    model_name: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code.value,
            "message": self.message,
            "retryable": self.retryable,
            "provider_name": self.provider_name,
            "model_name": self.model_name,
        }


class WritingRuntimeException(Exception):
    """Exception wrapper for structured runtime errors."""

    def __init__(self, error: WritingRuntimeError) -> None:
        super().__init__(error.message)
        self.error = error
