"""Persistence errors for canonical grammar lessons."""

from __future__ import annotations


class GrammarCanonicalLessonError(ValueError):
    """Raised when a canonical lesson persistence invariant is violated."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")
