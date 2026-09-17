"""Evidence Adapter (G3.4) — ExecutionResult → GrammarEvidenceObservation.

Executors never calculate Mastery / Review / Progression.
This adapter only normalizes declared evidence into observation contracts.
"""

from __future__ import annotations

from app.services.language_grammar.enums import (
    GrammarEvidenceSourceSkill,
    GrammarObservationType,
)
from app.services.language_grammar_activity_spec import ActivitySpecification
from app.services.language_grammar_evidence.types import GrammarEvidenceObservation
from app.services.language_grammar_skill_executor.types import (
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
)


def _map_evidence_kind(kind: str) -> GrammarObservationType:
    try:
        return GrammarObservationType(kind)
    except ValueError:
        return GrammarObservationType.formative


def adapt_execution_to_evidence(
    result: ExecutionResult,
    *,
    context: ExecutionContext,
    source_skill: GrammarEvidenceSourceSkill = GrammarEvidenceSourceSkill.grammar_lesson,
) -> tuple[GrammarEvidenceObservation, ...]:
    """Convert a completed (or failed) execution into normalized evidence observations.

    Never writes mastery. Never calls progression / review engines.
    """
    if result.status not in (ExecutionStatus.completed, ExecutionStatus.failed):
        return ()

    spec = context.specification
    observations: list[GrammarEvidenceObservation] = []
    for index, declaration in enumerate(spec.evidence):
        hint = (
            declaration.observation_types_hint[0]
            if declaration.observation_types_hint
            else declaration.evidence_kind
        )
        obs_type = _map_evidence_kind(hint)
        targets = declaration.grammar_targets or spec.grammar_targets or (spec.grammar_topic,)
        grammar_id = targets[0] if targets else spec.grammar_topic
        attempt_count = max(1, context.metadata.attempt_index + 1)
        correct_count = 1 if result.status is ExecutionStatus.completed else 0
        observations.append(
            GrammarEvidenceObservation(
                observation_id=f"{result.execution_id}:{declaration.evidence_id}:{index}",
                grammar_id=grammar_id,
                context=spec.step_id or "grammar_activity",
                attempt_count=attempt_count,
                correct_count=correct_count,
                observation_type=obs_type,
                source_skill=source_skill,
                student_id=context.student.student_id,
                language_id=context.student.language_id,
                observed_at=result.timing.finished_at or context.metadata.as_of or None,
                confidence=None,
            )
        )
    return tuple(observations)


def source_skill_for_executor(executor_id: str) -> GrammarEvidenceSourceSkill:
    """Deterministic source_skill from executor id — no Runtime skill if-branches."""
    mapping = {
        "speaking": GrammarEvidenceSourceSkill.speaking,
        "reading": GrammarEvidenceSourceSkill.reading,
        "listening": GrammarEvidenceSourceSkill.listening,
        "writing": GrammarEvidenceSourceSkill.writing,
        "conversation": GrammarEvidenceSourceSkill.speaking,
    }
    return mapping.get(executor_id, GrammarEvidenceSourceSkill.grammar_lesson)


def declarations_from_spec(spec: ActivitySpecification) -> tuple[str, ...]:
    """Helper for audits — evidence ids declared on the spec."""
    return tuple(d.evidence_id for d in spec.evidence)
