"""Types for language_speaking_evaluation_runtime (S7)."""

from __future__ import annotations

from dataclasses import dataclass, field

LANGUAGE_SPEAKING_EVALUATION_RUNTIME_VERSION = "7.0.0"


@dataclass(frozen=True, slots=True)
class SpeakingEvaluationTurnResult:
    """Legacy stub replaced by evaluation_pipeline.SpeakingEvaluationTurnResult."""

    stub: bool = False
    version: str = LANGUAGE_SPEAKING_EVALUATION_RUNTIME_VERSION
