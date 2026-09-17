"""Remediation, retry, and reinforcement decision rules (S9)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app.services.language_speaking_diagnostic.types import TargetSelectionReason
from app.services.language_speaking_lesson_planner.mission_types import SpeakingMissionOutcome
from app.services.language_speaking_lesson_planner.types import (
    SpeakingLearningSession,
    SpeakingSessionDecision,
    SpeakingSessionOutcomeKind,
    SpeakingSessionPhase,
    SpeakingTurnAccumulation,
)


def mission_flow_from_session_outcome(outcome: SpeakingSessionOutcomeKind) -> SpeakingMissionOutcome:
    """Map a session-boundary outcome to a mission-level runtime flow decision.

    Bridges the existing session-boundary enum (owned here) to the S10.1 mission flow
    contract without duplicating either. Retry semantics live in the mission flow model;
    they are never expressed as a mission kind.
    """
    return {
        SpeakingSessionOutcomeKind.session_complete: SpeakingMissionOutcome.complete,
        SpeakingSessionOutcomeKind.next_target_ready: SpeakingMissionOutcome.complete,
        SpeakingSessionOutcomeKind.reinforcement: SpeakingMissionOutcome.move_to_transfer,
        SpeakingSessionOutcomeKind.focused_retry: SpeakingMissionOutcome.retry_with_scaffold,
        SpeakingSessionOutcomeKind.remediation: SpeakingMissionOutcome.retry_same_task,
    }[outcome]

WEAK_TURN_PERFORMANCE = 0.42
STRONG_TURN_PERFORMANCE = 0.68
SESSION_WEAK_AVG = 0.45
SESSION_STRONG_AVG = 0.62
MIN_TURNS_FOR_DECISION = 1
REGRESSION_TURN_STREAK = 2


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _mint_decision_id(session_id: str, outcome: SpeakingSessionOutcomeKind) -> str:
    raw = f"s9-dec:{session_id}:{outcome.value}:{_now_iso()}"
    return f"dec-{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


def _target_turns(session: SpeakingLearningSession, target_skill_id: str) -> tuple[SpeakingTurnAccumulation, ...]:
    return tuple(t for t in session.turn_accumulations if t.target_skill_id == target_skill_id)


def _avg_performance(turns: tuple[SpeakingTurnAccumulation, ...]) -> float:
    if not turns:
        return 0.0
    return sum(t.performance for t in turns) / len(turns)


def _consecutive_weak(turns: tuple[SpeakingTurnAccumulation, ...]) -> int:
    streak = 0
    for t in reversed(turns):
        if t.performance < WEAK_TURN_PERFORMANCE:
            streak += 1
        else:
            break
    return streak


def decide_session_outcome(
    session: SpeakingLearningSession,
    *,
    primary_target_skill_id: str,
    selection_reason: str,
    min_communicative_turns: int,
) -> SpeakingSessionDecision:
    """Deterministic session boundary decision — one weak turn never regresses alone."""
    turns = _target_turns(session, primary_target_skill_id)
    avg = _avg_performance(turns)
    weak_streak = _consecutive_weak(turns)
    provenance: list[str] = [
        f"turns:{len(turns)}",
        f"avg_performance:{avg:.3f}",
        f"communicative_turns:{session.communicative_turns_completed}",
    ]

    if session.communicative_turns_completed < min_communicative_turns:
        return SpeakingSessionDecision(
            decision_id=_mint_decision_id(session.session_id, SpeakingSessionOutcomeKind.session_complete),
            outcome_kind=SpeakingSessionOutcomeKind.session_complete,
            detail="Session ended before minimum communicative turns — no penalty applied.",
            provenance=tuple(provenance + ["early_exit"]),
            next_phase=SpeakingSessionPhase.completed,
            retry_same_target=False,
            student_summary="Good effort today. Your next session will pick up where you left off.",
        )

    pronunciation_focus = selection_reason in (
        TargetSelectionReason.pronunciation_weakness.value,
        "pronunciation_weakness",
    )
    delivery_focus = selection_reason in (
        TargetSelectionReason.delivery_weakness.value,
        "delivery_weakness",
    )
    task_focus = selection_reason in (
        TargetSelectionReason.task_weakness.value,
        "task_weakness",
    )

    last = turns[-1] if turns else None
    if last and last.performance < WEAK_TURN_PERFORMANCE and weak_streak < REGRESSION_TURN_STREAK:
        provenance.append("single_weak_turn_no_regression")
        if pronunciation_focus or any("pronunciation" in t for t in last.mistake_tags):
            return SpeakingSessionDecision(
                decision_id=_mint_decision_id(session.session_id, SpeakingSessionOutcomeKind.focused_retry),
                outcome_kind=SpeakingSessionOutcomeKind.focused_retry,
                detail="One weak pronunciation turn — focused retry without regression.",
                provenance=tuple(provenance),
                next_phase=SpeakingSessionPhase.focused_retry,
                retry_same_target=True,
                student_summary="Let's try that sound again in a short, focused practice.",
            )
        if task_focus or last.source_dimension == "task_response":
            return SpeakingSessionDecision(
                decision_id=_mint_decision_id(session.session_id, SpeakingSessionOutcomeKind.remediation),
                outcome_kind=SpeakingSessionOutcomeKind.remediation,
                detail="One weak communicative turn — scenario remediation.",
                provenance=tuple(provenance),
                next_phase=SpeakingSessionPhase.remediation,
                retry_same_target=True,
                student_summary="Let's revisit the task with a clearer scenario.",
            )

    if weak_streak >= REGRESSION_TURN_STREAK or avg < SESSION_WEAK_AVG:
        if pronunciation_focus or delivery_focus:
            kind = SpeakingSessionOutcomeKind.focused_retry
            phase = SpeakingSessionPhase.focused_retry
            summary = "Focused practice on your target sound and delivery."
        elif task_focus:
            kind = SpeakingSessionOutcomeKind.remediation
            phase = SpeakingSessionPhase.remediation
            summary = "Extra communicative practice on today's goal."
        else:
            kind = SpeakingSessionOutcomeKind.focused_retry
            phase = SpeakingSessionPhase.focused_retry
            summary = "Let's consolidate today's target with another short practice."
        return SpeakingSessionDecision(
            decision_id=_mint_decision_id(session.session_id, kind),
            outcome_kind=kind,
            detail=f"Repeated weakness detected (avg={avg:.2f}, streak={weak_streak}).",
            provenance=tuple(provenance + [f"weak_streak:{weak_streak}"]),
            next_phase=phase,
            retry_same_target=True,
            student_summary=summary,
        )

    if avg >= SESSION_STRONG_AVG and all(t.success for t in turns[-2:]) if len(turns) >= 2 else avg >= SESSION_STRONG_AVG:
        return SpeakingSessionDecision(
            decision_id=_mint_decision_id(session.session_id, SpeakingSessionOutcomeKind.reinforcement),
            outcome_kind=SpeakingSessionOutcomeKind.reinforcement,
            detail="Strong session performance on target skill.",
            provenance=tuple(provenance + ["strong_session"]),
            next_phase=SpeakingSessionPhase.reinforced,
            retry_same_target=False,
            student_summary="Great work! You showed solid progress on today's focus.",
        )

    return SpeakingSessionDecision(
        decision_id=_mint_decision_id(session.session_id, SpeakingSessionOutcomeKind.session_complete),
        outcome_kind=SpeakingSessionOutcomeKind.session_complete,
        detail="Session complete — ready for next eligible target.",
        provenance=tuple(provenance),
        next_phase=SpeakingSessionPhase.completed,
        retry_same_target=False,
        student_summary="Session complete. Your speaking journey has been updated.",
    )
