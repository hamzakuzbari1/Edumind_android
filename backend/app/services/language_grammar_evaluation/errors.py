"""Grammar-Constrained Evaluation errors (V1.8)."""

from __future__ import annotations


class GrammarEvaluationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class EvaluationValidationError(GrammarEvaluationError):
    """Invalid evaluation request or malformed evidence."""


class EvaluationDisabledError(GrammarEvaluationError):
    """Evaluation gated off by feature flags."""
