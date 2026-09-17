"""Listening Learning Stage Engine (Phase 5.1 / 5.1.1 / 5.2).

Official CEFR → Learning Stage (persistent) → Transition Gate → Eligibility → Explicit Transition.

Phase 5.1.1: stage_score is a live metric; persistent stage advances only when the transition gate passes.
Phase 5.2: eligibility requires all transition gate requirements (AND logic).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_learning_stage.scoring import (
    compute_signal_contributions,
    compute_stage_score,
    score_to_band,
)
from app.services.language_learning_stage.signals import gather_listening_signals
from app.services.language_learning_stage.storage import load_listening_stage, save_listening_stage
from app.services.language_learning_stage.telemetry import build_stage_result
from app.services.language_learning_stage.types import (
    LearningStageResult,
    ListeningLearningStage,
    ListeningSignalSnapshot,
    StageTransitionEligibility,
)
from app.services.language_progression_service import get_official_cefr
from app.services.language_transition_gate.engine import (
    build_gate_context,
    evaluate_transition_gate,
    gate_to_eligibility_conditions,
)


def _gate_context_from_snapshot(
    *,
    official_cefr: str,
    persistent_stage: int,
    stage_score: int,
    snapshot: ListeningSignalSnapshot,
) -> object:
    return build_gate_context(
        official_cefr=official_cefr,
        persistent_stage=persistent_stage,
        stage_score=stage_score,
        snapshot=snapshot,
        challenge_level=snapshot.challenge_level,
        demote_streak=snapshot.demote_streak,
        pending_review_count=snapshot.pending_review_count,
        review_due_objectives=snapshot.review_due_objectives,
        needs_evidence_objectives=snapshot.needs_evidence_objectives,
        missing_speaker_evidence=snapshot.missing_speaker_evidence,
        missing_inference_evidence=snapshot.missing_inference_evidence,
    )


def _eligibility_from_gate(gate) -> StageTransitionEligibility:
    if gate.next_stage is None:
        return StageTransitionEligibility(
            eligible_for_next_stage=False,
            reason=gate.primary_blocker or "No further learning stage available.",
            required_conditions=gate_to_eligibility_conditions(gate),
            next_stage=None,
        )
    if gate.eligible:
        reason = (
            f"All {len(gate.requirements)} transition gate requirements passed; "
            "explicit transition may be applied."
        )
    else:
        reason = gate.primary_blocker or "Transition gate requirements not met."
    return StageTransitionEligibility(
        eligible_for_next_stage=gate.eligible,
        reason=reason,
        required_conditions=gate_to_eligibility_conditions(gate),
        next_stage=gate.next_stage,
    )


def _build_result_from_signals(
    *,
    official_cefr: str,
    persistent_stage: int,
    snapshot: ListeningSignalSnapshot,
) -> LearningStageResult:
    """Pure evaluation — persistent stage is never mutated by score."""
    stage = ListeningLearningStage(max(1, min(3, persistent_stage)))
    contributions = compute_signal_contributions(snapshot)
    stage_score = compute_stage_score(contributions)
    stage_band = score_to_band(stage_score)

    gate = evaluate_transition_gate(
        _gate_context_from_snapshot(
            official_cefr=official_cefr,
            persistent_stage=int(stage),
            stage_score=stage_score,
            snapshot=snapshot,
        )
    )
    eligibility = _eligibility_from_gate(gate)
    progress = gate.estimated_remaining_progress

    return build_stage_result(
        official_cefr=official_cefr.upper(),
        persistent_stage=stage,
        stage_score=stage_score,
        stage_band=stage_band,
        eligibility=eligibility,
        contributions=contributions,
        progress_to_next=progress,
        lesson_index=snapshot.lesson_index,
        mastered_objectives=snapshot.mastered_objectives,
        total_objectives=snapshot.total_objectives,
        transition_gate=gate,
    )


async def evaluate_listening_learning_stage(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    official_cefr: str | None = None,
) -> LearningStageResult:
    """Compute live stage score + gate eligibility — does not change persistent stage."""
    if official_cefr is None:
        official_read = await get_official_cefr(
            db, student_id=student_id, language_id=language_id, skill="listening"
        )
        official_cefr = official_read.level.value

    persistent_stage = await load_listening_stage(db, student_id=student_id, language_id=language_id)
    snapshot = await gather_listening_signals(
        db,
        student_id=student_id,
        language_id=language_id,
        official_cefr=official_cefr,
    )
    return _build_result_from_signals(
        official_cefr=official_cefr,
        persistent_stage=persistent_stage,
        snapshot=snapshot,
    )


async def apply_listening_stage_transition(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    target_stage: int,
    official_cefr: str | None = None,
) -> LearningStageResult:
    """Explicit transition only — never demotes; requires full transition gate pass."""
    result = await evaluate_listening_learning_stage(
        db,
        student_id=student_id,
        language_id=language_id,
        official_cefr=official_cefr,
    )
    current = result.current_stage
    target = max(1, min(3, int(target_stage)))

    if target < current:
        return result
    if target == current:
        return result
    if target > current + 1:
        return result
    if not result.eligible_for_next_stage:
        return result

    await save_listening_stage(
        db,
        student_id=student_id,
        language_id=language_id,
        stage=target,
        official_cefr=result.official_cefr,
        stage_score=result.stage_score,
        previous_stage=current,
    )
    return await evaluate_listening_learning_stage(
        db,
        student_id=student_id,
        language_id=language_id,
        official_cefr=result.official_cefr,
    )


async def evaluate_and_persist_listening_stage(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    official_cefr: str | None = None,
) -> LearningStageResult:
    """Evaluate stage and persist a one-step advance when the transition gate passes."""
    result = await evaluate_listening_learning_stage(
        db,
        student_id=student_id,
        language_id=language_id,
        official_cefr=official_cefr,
    )
    if (
        result.eligible_for_next_stage
        and result.next_stage is not None
        and result.next_stage == result.current_stage + 1
    ):
        result = await apply_listening_stage_transition(
            db,
            student_id=student_id,
            language_id=language_id,
            target_stage=result.next_stage,
            official_cefr=result.official_cefr,
        )
    return result
