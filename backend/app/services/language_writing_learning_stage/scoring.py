"""Writing stage score — weighted mastery signals (not lesson count)."""

from __future__ import annotations

from app.services.language_writing_learning_stage.types import WritingSignalSnapshot

# Weights sum to 1.0. Educational quality signals (task response, organization,
# CEFR alignment) are weighted alongside grammar/vocabulary so strong grammar
# alone cannot carry the stage score.
SIGNAL_WEIGHTS: dict[str, float] = {
    "grammar_mastery": 0.16,
    "vocabulary_mastery": 0.14,
    "task_response": 0.16,
    "organization": 0.10,
    "cefr_alignment": 0.10,
    "revision_quality": 0.12,
    "confidence": 0.08,
    "evidence_coverage": 0.08,
    "stability": 0.06,
}

# Max fraction the stage score is reduced when mistakes keep recurring.
REPEATED_MISTAKE_PENALTY = 0.12


def compute_writing_stage_score(snapshot: WritingSignalSnapshot) -> int:
    weighted = (
        snapshot.grammar_mastery_avg * SIGNAL_WEIGHTS["grammar_mastery"]
        + snapshot.vocabulary_mastery_avg * SIGNAL_WEIGHTS["vocabulary_mastery"]
        + snapshot.task_response_avg * SIGNAL_WEIGHTS["task_response"]
        + snapshot.organization_avg * SIGNAL_WEIGHTS["organization"]
        + snapshot.cefr_alignment_avg * SIGNAL_WEIGHTS["cefr_alignment"]
        + snapshot.revision_quality_avg * SIGNAL_WEIGHTS["revision_quality"]
        + snapshot.confidence_avg * SIGNAL_WEIGHTS["confidence"]
        + snapshot.evidence_coverage_avg * SIGNAL_WEIGHTS["evidence_coverage"]
        + snapshot.recent_stability * SIGNAL_WEIGHTS["stability"]
    )
    penalty = 1.0 - snapshot.repeated_mistake_ratio * REPEATED_MISTAKE_PENALTY
    return max(0, min(100, int(round(weighted * penalty * 100))))


def score_to_band(score: int) -> str:
    if score >= 80:
        return "Advanced"
    if score >= 40:
        return "Intermediate"
    return "Beginner"
