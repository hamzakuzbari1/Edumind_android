"""Pipeline orchestration errors (Integration Phase 1)."""

from __future__ import annotations


class GrammarPipelineError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class PipelineDisabledError(GrammarPipelineError):
    pass


class PipelineValidationError(GrammarPipelineError):
    pass


class PipelineStageError(GrammarPipelineError):
    def __init__(self, stage: str, code: str, message: str) -> None:
        self.stage = stage
        super().__init__(code, message)
