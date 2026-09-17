"""Writing transition gate — AND logic; lesson count is one requirement, never sole driver."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing_learning_stage.types import WritingLearningStage, WritingSignalSnapshot

REQUIREMENT_STAGE_SCORE = "stage_score"
REQUIREMENT_GRAMMAR = "grammar_mastery"
REQUIREMENT_VOCABULARY = "vocabulary_mastery"
REQUIREMENT_TASK_RESPONSE = "task_response"
REQUIREMENT_CEFR_ALIGNMENT = "cefr_alignment"
REQUIREMENT_REVISION = "revision_quality"
REQUIREMENT_CONFIDENCE = "confidence_trend"
REQUIREMENT_EVIDENCE = "evidence_coverage"
REQUIREMENT_STABILITY = "stability"
REQUIREMENT_LESSON_EXPOSURE = "minimum_lesson_exposure"


@dataclass(frozen=True, slots=True)
class WritingGateRequirementResult:
    name: str
    current: str
    required: str
    passed: bool
    message: str


@dataclass(frozen=True, slots=True)
class WritingTransitionGateResult:
    eligible: bool
    overall_gate_score: float
    requirements: tuple[WritingGateRequirementResult, ...]
    primary_blocker: str | None
    next_stage: int | None
    estimated_remaining_progress: float


@dataclass(frozen=True, slots=True)
class WritingGateThresholds:
    min_stage_score: int
    min_grammar: float
    min_vocabulary: float
    min_task_response: float
    min_cefr_alignment: float
    min_revision: float
    min_confidence: float
    min_evidence: float
    min_stability: float
    min_lesson_exposure: int


GATE_THRESHOLDS: dict[tuple[int, int], WritingGateThresholds] = {
    (1, 2): WritingGateThresholds(
        min_stage_score=40,
        min_grammar=0.62,
        min_vocabulary=0.55,
        min_task_response=0.55,
        min_cefr_alignment=0.50,
        min_revision=0.55,
        min_confidence=0.60,
        min_evidence=0.50,
        min_stability=0.52,
        min_lesson_exposure=4,
    ),
    (2, 3): WritingGateThresholds(
        min_stage_score=80,
        min_grammar=0.72,
        min_vocabulary=0.68,
        min_task_response=0.70,
        min_cefr_alignment=0.65,
        min_revision=0.68,
        min_confidence=0.72,
        min_evidence=0.65,
        min_stability=0.62,
        min_lesson_exposure=8,
    ),
}


def _pct(v: float) -> str:
    return f"{round(v * 100)}"


def evaluate_writing_transition_gate(
    *,
    persistent_stage: int,
    stage_score: int,
    snapshot: WritingSignalSnapshot,
) -> WritingTransitionGateResult:
    stage = max(1, min(3, persistent_stage))
    if stage >= int(WritingLearningStage.advanced):
        return WritingTransitionGateResult(
            eligible=False,
            overall_gate_score=100.0,
            requirements=(),
            primary_blocker="Already at Advanced — complete the Writing Promotion Assessment.",
            next_stage=None,
            estimated_remaining_progress=100.0,
        )
    next_stage = stage + 1
    t = GATE_THRESHOLDS[(stage, next_stage)]
    reqs: list[WritingGateRequirementResult] = [
        WritingGateRequirementResult(
            REQUIREMENT_STAGE_SCORE,
            str(stage_score),
            str(t.min_stage_score),
            stage_score >= t.min_stage_score,
            f"Stage score {stage_score} / {t.min_stage_score}.",
        ),
        WritingGateRequirementResult(
            REQUIREMENT_GRAMMAR,
            _pct(snapshot.grammar_mastery_avg),
            _pct(t.min_grammar),
            snapshot.grammar_mastery_avg >= t.min_grammar,
            f"Grammar mastery {_pct(snapshot.grammar_mastery_avg)}% / {_pct(t.min_grammar)}%.",
        ),
        WritingGateRequirementResult(
            REQUIREMENT_VOCABULARY,
            _pct(snapshot.vocabulary_mastery_avg),
            _pct(t.min_vocabulary),
            snapshot.vocabulary_mastery_avg >= t.min_vocabulary,
            f"Vocabulary mastery {_pct(snapshot.vocabulary_mastery_avg)}% / {_pct(t.min_vocabulary)}%.",
        ),
        WritingGateRequirementResult(
            REQUIREMENT_TASK_RESPONSE,
            _pct(snapshot.task_response_avg),
            _pct(t.min_task_response),
            snapshot.task_response_avg >= t.min_task_response,
            f"Task response {_pct(snapshot.task_response_avg)}% / {_pct(t.min_task_response)}% — answer the prompt fully.",
        ),
        WritingGateRequirementResult(
            REQUIREMENT_CEFR_ALIGNMENT,
            _pct(snapshot.cefr_alignment_avg),
            _pct(t.min_cefr_alignment),
            snapshot.cefr_alignment_avg >= t.min_cefr_alignment,
            f"CEFR alignment {_pct(snapshot.cefr_alignment_avg)}% / {_pct(t.min_cefr_alignment)}% — write consistently at your level.",
        ),
        WritingGateRequirementResult(
            REQUIREMENT_REVISION,
            _pct(snapshot.revision_quality_avg),
            _pct(t.min_revision),
            snapshot.revision_quality_avg >= t.min_revision,
            f"Revision quality {_pct(snapshot.revision_quality_avg)}% / {_pct(t.min_revision)}%.",
        ),
        WritingGateRequirementResult(
            REQUIREMENT_CONFIDENCE,
            _pct(snapshot.confidence_avg),
            _pct(t.min_confidence),
            snapshot.confidence_avg >= t.min_confidence,
            f"Writing confidence {_pct(snapshot.confidence_avg)}% / {_pct(t.min_confidence)}%.",
        ),
        WritingGateRequirementResult(
            REQUIREMENT_EVIDENCE,
            _pct(snapshot.evidence_coverage_avg),
            _pct(t.min_evidence),
            snapshot.evidence_coverage_avg >= t.min_evidence,
            f"Evidence coverage {_pct(snapshot.evidence_coverage_avg)}% / {_pct(t.min_evidence)}%.",
        ),
        WritingGateRequirementResult(
            REQUIREMENT_STABILITY,
            _pct(snapshot.recent_stability),
            _pct(t.min_stability),
            snapshot.recent_stability >= t.min_stability,
            f"Performance stability {_pct(snapshot.recent_stability)}% / {_pct(t.min_stability)}%.",
        ),
        WritingGateRequirementResult(
            REQUIREMENT_LESSON_EXPOSURE,
            str(snapshot.lesson_index),
            str(t.min_lesson_exposure),
            snapshot.lesson_index >= t.min_lesson_exposure,
            f"Lesson exposure {snapshot.lesson_index} / {t.min_lesson_exposure} (supporting only).",
        ),
    ]
    failed = [r for r in reqs if not r.passed]
    eligible = len(failed) == 0
    progress_parts = [100.0 if r.passed else min(99.0, float(r.current.rstrip("%") or 0) / max(float(r.required.rstrip("%") or 1), 1) * 100) for r in reqs]
    overall = round(sum(progress_parts) / len(progress_parts), 1) if progress_parts else 0.0
    remaining = 100.0 if eligible else max(0.0, 100.0 - overall)
    return WritingTransitionGateResult(
        eligible=eligible,
        overall_gate_score=overall,
        requirements=tuple(reqs),
        primary_blocker=failed[0].message if failed else None,
        next_stage=next_stage,
        estimated_remaining_progress=remaining,
    )
