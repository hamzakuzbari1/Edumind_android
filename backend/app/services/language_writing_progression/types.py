"""Types for Writing Progression Runtime (W0)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_writing.enums import OfficialWritingCEFR


@dataclass(frozen=True, slots=True)
class WritingConfidenceSnapshot:
    """Internal — not exposed to student frontend."""

    overall: float
    organization: float = 0.0
    grammar: float = 0.0
    lexis: float = 0.0
    task_achievement: float = 0.0
    register: float = 0.0
    complexity_mastery: float = 0.0


@dataclass(frozen=True, slots=True)
class WritingEvidenceSnapshot:
    """Internal evidence axes for progression."""

    genres_completed: tuple[str, ...] = ()
    chain_nodes_completed: tuple[str, ...] = ()
    arc_stages_touched: tuple[str, ...] = ()
    complexity_levels_passed: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class WritingChallengeSnapshot:
    """Internal challenge state."""

    challenge_level: str
    context_complexity_delta: int = 0
    scaffolding_reduced: bool = False


@dataclass(frozen=True, slots=True)
class WritingProgressionResult:
    """Output of run_writing_progression_after_complete (contract only — W0)."""

    student_id: int
    language_id: int
    content_item_id: int
    official_cefr: OfficialWritingCEFR
    confidence: WritingConfidenceSnapshot
    evidence: WritingEvidenceSnapshot
    challenge: WritingChallengeSnapshot
    learning_stage: int
    stage_advanced: bool = False
    readiness_score: float | None = None
    stability_score: float | None = None
