"""Map evaluation results → GrammarEvidenceObservation (V1.8).

Never writes Mastery / Progression / Review.
"""

from __future__ import annotations

from app.services.language_grammar.enums import (
    GrammarEvidenceSourceSkill,
    GrammarObservationType,
)
from app.services.language_grammar_evaluation.types import (
    GrammarEvidenceItem,
    PatternEvaluationResult,
    PatternStatus,
)
from app.services.language_grammar_evidence.types import GrammarEvidenceObservation


def _source_skill(code: str) -> GrammarEvidenceSourceSkill:
    try:
        return GrammarEvidenceSourceSkill(code)
    except ValueError:
        return GrammarEvidenceSourceSkill.grammar_lesson


def pattern_results_to_evidence_items(
    pattern_results: tuple[PatternEvaluationResult, ...],
    *,
    timestamp: str = "",
) -> tuple[GrammarEvidenceItem, ...]:
    items: list[GrammarEvidenceItem] = []
    for result in pattern_results:
        if result.status is PatternStatus.not_applicable:
            continue
        if result.status is PatternStatus.unexpected:
            # Unexpected grammar is validation-rejected upstream; skip scoring.
            continue
        correct = result.status is PatternStatus.correct
        items.append(
            GrammarEvidenceItem(
                grammar_target=result.grammar_target,
                pattern=result.pattern,
                correct=correct,
                confidence=float(result.confidence),
                reason=result.reason,
                source_sentence=result.source_sentence,
                timestamp=timestamp,
            )
        )
    return tuple(items)


def evidence_items_to_observations(
    items: tuple[GrammarEvidenceItem, ...],
    *,
    evaluation_id: str,
    student_id: int,
    language_id: int,
    source_skill: str = "grammar_lesson",
    observed_at: str = "",
) -> tuple[GrammarEvidenceObservation, ...]:
    skill = _source_skill(source_skill)
    observations: list[GrammarEvidenceObservation] = []
    for index, item in enumerate(items):
        observations.append(
            GrammarEvidenceObservation(
                observation_id=f"{evaluation_id}:{item.grammar_target}:{index}",
                grammar_id=item.grammar_target,
                context=item.pattern,
                attempt_count=1,
                correct_count=1 if item.correct else 0,
                observation_type=GrammarObservationType.formative,
                source_skill=skill,
                student_id=student_id,
                language_id=language_id,
                observed_at=item.timestamp or observed_at or None,
                confidence=item.confidence,
                accuracy_signal=100.0 if item.correct else 0.0,
                understanding_signal=None,
                fluency_signal=None,  # explicitly out of scope
                retention_signal=None,
            )
        )
    return tuple(observations)
