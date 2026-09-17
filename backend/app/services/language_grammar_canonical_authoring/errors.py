"""Errors for the offline canonical grammar authoring workflow."""

from __future__ import annotations


class GrammarCanonicalAuthoringWorkflowError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")
