"""Speaking Domain validation (V1.2A)."""

from __future__ import annotations

from app.services.language_grammar.id_canon import is_canonical_grammar_id, normalize_grammar_id
from app.services.language_grammar_speaking.enums import (
    SpeakingAttemptStatus,
    SpeakingSessionStatus,
    SpeakingTurnStatus,
)
from app.services.language_grammar_speaking.errors import SpeakingValidationError
from app.services.language_grammar_speaking.types import (
    SpeakingAttempt,
    SpeakingContext,
    SpeakingSession,
    SpeakingTurn,
)


def validate_grammar_targets(targets: tuple[str, ...]) -> tuple[str, ...]:
    if not targets:
        raise SpeakingValidationError("missing_grammar_targets", "grammar_targets required")
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in targets:
        gid = normalize_grammar_id(raw)
        if not is_canonical_grammar_id(gid):
            raise SpeakingValidationError("invalid_grammar_target", f"Invalid grammar_id: {raw!r}")
        if gid in seen:
            raise SpeakingValidationError("duplicate_grammar_target", gid)
        seen.add(gid)
        normalized.append(gid)
    return tuple(normalized)


def validate_context(context: SpeakingContext) -> None:
    if context.student_id <= 0:
        raise SpeakingValidationError("invalid_student_id", "student_id must be positive")
    if context.language_id <= 0:
        raise SpeakingValidationError("invalid_language_id", "language_id must be positive")
    if not (context.activity_id or "").strip():
        raise SpeakingValidationError("missing_activity_id", "activity_id required")
    validate_grammar_targets(context.grammar_targets)


def validate_session(session: SpeakingSession) -> None:
    if not (session.session_id or "").strip():
        raise SpeakingValidationError("missing_session_id", "session_id required")
    if not (session.activity_id or "").strip():
        raise SpeakingValidationError("missing_activity_id", "activity_id required")
    if session.student_id <= 0:
        raise SpeakingValidationError("invalid_student_id", "student_id must be positive")
    validate_grammar_targets(session.grammar_targets)


def validate_turn_order(turns: tuple[SpeakingTurn, ...]) -> None:
    if not turns:
        return
    sequences = [t.sequence for t in turns]
    if sequences != sorted(sequences):
        raise SpeakingValidationError("invalid_turn_order", "turn sequences must be ascending")
    if len(set(sequences)) != len(sequences):
        raise SpeakingValidationError("duplicate_turn_sequence", "turn sequences must be unique")
    expected = list(range(1, len(turns) + 1))
    if sequences != expected and sequences != list(range(0, len(turns))):
        # Allow 0-based or 1-based contiguous sequences
        if sequences != list(range(sequences[0], sequences[0] + len(turns))):
            raise SpeakingValidationError(
                "non_contiguous_turn_order",
                f"expected contiguous sequences, got {sequences}",
            )


def validate_attempt_state(attempt: SpeakingAttempt) -> None:
    if not (attempt.attempt_id or "").strip():
        raise SpeakingValidationError("missing_attempt_id", "attempt_id required")
    if attempt.attempt_number < 1:
        raise SpeakingValidationError("invalid_attempt_number", "attempt_number must be >= 1")
    validate_turn_order(attempt.turns)
    open_turns = [t for t in attempt.turns if t.status is SpeakingTurnStatus.open]
    if attempt.status is SpeakingAttemptStatus.finished and open_turns:
        raise SpeakingValidationError(
            "open_turns_on_finished_attempt",
            "finished attempt cannot have open turns",
        )


def validate_session_state(session: SpeakingSession) -> None:
    validate_session(session)
    for attempt in session.attempts:
        validate_attempt_state(attempt)
    if session.status is SpeakingSessionStatus.completed and session.result is None:
        raise SpeakingValidationError(
            "completed_without_result",
            "completed session requires SpeakingResult",
        )
    if session.current_attempt_id:
        ids = {a.attempt_id for a in session.attempts}
        if session.current_attempt_id not in ids:
            raise SpeakingValidationError(
                "unknown_current_attempt",
                session.current_attempt_id,
            )
