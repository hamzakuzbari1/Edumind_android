"""SpeakingEvidence → GrammarEvidenceObservation (V1.2A).

Never calculates mastery / review / progression.
"""

from __future__ import annotations

from app.services.language_grammar.enums import (
    GrammarEvidenceSourceSkill,
    GrammarObservationType,
)
from app.services.language_grammar_evidence.types import GrammarEvidenceObservation
from app.services.language_grammar_speaking.enums import SpeakingCompletionState
from app.services.language_grammar_speaking.errors import SpeakingValidationError
from app.services.language_grammar_speaking.types import (
    SpeakingContext,
    SpeakingEvidence,
    SpeakingResult,
    SpeakingSession,
)
from app.services.language_grammar_speaking.validation import validate_grammar_targets


def _map_observation_type(hint: str) -> GrammarObservationType:
    try:
        return GrammarObservationType(hint)
    except ValueError:
        return GrammarObservationType.formative


def build_speaking_evidence(
    session: SpeakingSession,
    *,
    attempt_id: str,
    result: SpeakingResult,
    context_label: str = "speaking_activity",
) -> SpeakingEvidence:
    """Project a SpeakingResult into a domain SpeakingEvidence envelope."""
    targets = validate_grammar_targets(session.grammar_targets)
    correct = 1 if result.completion_state is SpeakingCompletionState.complete else 0
    attempt = next((a for a in session.attempts if a.attempt_id == attempt_id), None)
    attempt_count = attempt.attempt_number if attempt is not None else 1
    return SpeakingEvidence(
        evidence_id=f"sev_{session.session_id}_{attempt_id}",
        session_id=session.session_id,
        attempt_id=attempt_id,
        grammar_targets=targets,
        observation_type_hint="formative",
        attempt_count=max(1, attempt_count),
        correct_count=correct,
        context=context_label,
        notes=result.notes,
    )


def map_speaking_evidence_to_observations(
    evidence: SpeakingEvidence,
    *,
    context: SpeakingContext,
    observed_at: str = "",
) -> tuple[GrammarEvidenceObservation, ...]:
    """Normalize SpeakingEvidence into GrammarEvidenceObservation tuples.

    Does NOT call Mastery. Does NOT score.
    """
    if not evidence.grammar_targets:
        raise SpeakingValidationError("missing_grammar_targets", "evidence requires grammar_targets")
    observations: list[GrammarEvidenceObservation] = []
    for index, grammar_id in enumerate(evidence.grammar_targets):
        observations.append(
            GrammarEvidenceObservation(
                observation_id=f"{evidence.evidence_id}:{grammar_id}:{index}",
                grammar_id=grammar_id,
                context=evidence.context or "speaking_activity",
                attempt_count=max(1, evidence.attempt_count),
                correct_count=max(0, min(evidence.correct_count, evidence.attempt_count)),
                observation_type=_map_observation_type(evidence.observation_type_hint),
                source_skill=GrammarEvidenceSourceSkill.speaking,
                student_id=context.student_id,
                language_id=context.language_id,
                observed_at=observed_at or None,
                confidence=None,
            )
        )
    return tuple(observations)


def map_session_result_to_observations(
    session: SpeakingSession,
    *,
    context: SpeakingContext,
    attempt_id: str | None = None,
    observed_at: str = "",
) -> tuple[GrammarEvidenceObservation, ...]:
    """Convenience: session.result → observations via SpeakingEvidence."""
    if session.result is None:
        return ()
    aid = attempt_id or session.current_attempt_id or (
        session.attempts[-1].attempt_id if session.attempts else "attempt_0"
    )
    evidence = build_speaking_evidence(session, attempt_id=aid, result=session.result)
    return map_speaking_evidence_to_observations(
        evidence,
        context=context,
        observed_at=observed_at or session.updated_at,
    )
