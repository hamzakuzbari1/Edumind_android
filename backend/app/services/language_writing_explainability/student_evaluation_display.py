"""Student-safe evaluation display (W7 UX) — renders canonical evaluation only."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.language_writing_evaluator.evaluation_facts_types import CriterionStatus
from app.services.language_writing_evaluator.evaluation_result import WritingEvaluationEngineResult

STUDENT_EVALUATION_DISPLAY_VERSION = "8.2.0"

_DIMENSION_LABELS = {
    "grammar": "Grammar",
    "vocabulary": "Vocabulary",
    "organization": "Organization",
    "task_completion": "Task Completion",
    "goal_alignment": "Goal Alignment",
}

# Criteria phrased as length/word-count gates — a miss means "not attempted enough",
# never "attempted inaccurately".
_LENGTH_TOKENS = ("word", "words", "length", "at least", "minimum")

# Instruction words in criterion labels that carry no target-structure meaning.
_CRIT_STOP = frozenset(
    """use using used correct correctly clear clearly write writing written include including
    make making your with this that these those about into more than least word words sentence
    sentences paragraph paragraphs draft text""".split()
)


def _dimension_status(passed: bool) -> str:
    return "on_track" if passed else "needs_work"


def _attempt_evidence(evaluation: WritingEvaluationEngineResult) -> str:
    """Lower-cased grammar evidence used to tell 'attempted-but-wrong' from 'missing'."""
    parts: list[str] = list(evaluation.grammar.errors)
    claude = evaluation.claude_analysis
    if claude and claude.available:
        for note in claude.grammar_notes:
            parts.extend((note.issue, note.rule, note.fix, note.example))
    return " ".join(p for p in parts if p).lower()


def _criterion_display_status(
    label: str,
    status: CriterionStatus,
    evidence_low: str,
) -> str:
    """Four-state, student-facing status — explanation quality only.

    Never changes readiness ownership: the canonical `status` (met/partial/not_met)
    still drives all gating. This only tells the student *how* a criterion is unmet.
    """
    if status == CriterionStatus.met:
        return "met"
    if status == CriterionStatus.partial:
        return "partially_met"

    low = (label or "").lower()
    if any(tok in low for tok in _LENGTH_TOKENS):
        return "not_attempted"

    keywords = [w for w in re.findall(r"[a-z]+", low) if len(w) > 3 and w not in _CRIT_STOP]
    for kw in keywords:
        stem = kw[:-1] if kw.endswith("s") else kw
        if kw in evidence_low or stem in evidence_low:
            return "attempted_inaccurately"
    return "not_attempted"


@dataclass(frozen=True, slots=True)
class StudentEvaluationDisplay:
    """Evaluation panel payload — no scores or internal weights."""

    dimensions: tuple[dict[str, object], ...]
    success_criteria: tuple[dict[str, object], ...]
    strengths: tuple[str, ...]
    improvements: tuple[str, ...]
    ready_to_complete: bool
    display_version: str = STUDENT_EVALUATION_DISPLAY_VERSION

    def to_student_dict(self) -> dict[str, object]:
        return {
            "dimensions": list(self.dimensions),
            "success_criteria": list(self.success_criteria),
            "strengths": list(self.strengths),
            "improvements": list(self.improvements),
            "ready_to_complete": self.ready_to_complete,
            "display_version": self.display_version,
        }


def build_student_evaluation_display(
    evaluation: WritingEvaluationEngineResult,
) -> StudentEvaluationDisplay:
    """Build student evaluation panel — render-only from canonical result."""
    dimensions = tuple(
        {
            "key": dim.dimension,
            "label": _DIMENSION_LABELS.get(dim.dimension, dim.dimension.replace("_", " ").title()),
            "status": _dimension_status(dim.passed),
        }
        for dim in (
            evaluation.grammar,
            evaluation.vocabulary,
            evaluation.organization,
            evaluation.task_completion,
            evaluation.goal_alignment,
        )
    )
    evidence_low = _attempt_evidence(evaluation)
    criteria = tuple(
        {
            "label": item.label,
            "status": item.status.value,
            "display_status": _criterion_display_status(item.label, item.status, evidence_low),
        }
        for item in evaluation.success_criteria
    )
    return StudentEvaluationDisplay(
        dimensions=dimensions,
        success_criteria=criteria,
        strengths=evaluation.explanation.strengths[:3],
        # Improvements are a SHORT summary only — detailed coaching lives in the
        # Teacher Analysis (grammar_notes) and the Coach (next revision).
        improvements=evaluation.explanation.improvements[:3],
        ready_to_complete=evaluation.revision_readiness.ready,
    )
