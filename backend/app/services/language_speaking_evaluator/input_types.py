"""Plain input/context objects for the speaking evaluator (S7).

Assembled by evaluation_runtime — evaluator must not import audio_frontend or curriculum.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_speaking_pronunciation.types import SpeakingPronunciationEvidenceResult
from app.services.language_speaking_prosody.types import SpeakingProsodyEvidenceResult


@dataclass(frozen=True, slots=True)
class SpeakingTaskContext:
    task_id: str
    task_type: str
    task_prompt: str
    task_instructions: str
    success_criteria: tuple[str, ...] = ()
    target_skill_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SpeakingGoalContext:
    speaking_goal: str
    goal_label: str


@dataclass(frozen=True, slots=True)
class SpeakingOfficialCefrContext:
    official_cefr: str
    band_descriptor: str = ""


@dataclass(frozen=True, slots=True)
class SpeakingEvaluationInput:
    """Evidence bundle facts passed into the evaluator — no raw audio bytes."""

    transcript_text: str
    transcript_word_count: int = 0
    transcript_tokens: tuple[str, ...] = ()
    pause_count: int = 0
    pronunciation: SpeakingPronunciationEvidenceResult | None = None
    prosody: SpeakingProsodyEvidenceResult | None = None
    evidence_availability: dict[str, bool] = field(default_factory=dict)
    evidence_reliability: float = 0.0
    provider_provenance: tuple[dict[str, object], ...] = ()
    evidence_reference_ids: tuple[str, ...] = ()
    processing_warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SpeakingEvaluationContext:
    evaluation_id: str
    student_id: int
    language_id: int
    session_id: str
    task_id: str
    attempt_id: str
    revision_number: int
    evaluated_at: str
    task: SpeakingTaskContext
    goal: SpeakingGoalContext
    official_cefr: SpeakingOfficialCefrContext
    previous_attempt_summary: str = ""
    force_complete: bool = False
