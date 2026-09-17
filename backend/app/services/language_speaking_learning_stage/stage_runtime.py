"""Speaking learning-stage persistence runtime (S16).

Sole writer of ``learning_stage_speaking``. Rebuilds S15 snapshot under row lock,
runs the pure transition gate, and applies one-step advances only.

Never mutates ``official_speaking_cefr``, promotion readiness decisions, or S2.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_progression_service import ensure_progression_row
from app.services.language_speaking.enums import SpeakingLearningStage
from app.services.language_speaking_knowledge_model.locking import lock_speaking_progression_row
from app.services.language_speaking_knowledge_model.storage import (
    knowledge_model_from_speaking_bucket,
    speaking_bucket_from_payload,
)
from app.services.language_speaking_learning_stage.signals import gather_speaking_stage_signals
from app.services.language_speaking_learning_stage.types import SpeakingStageSignalSnapshot
from app.services.language_speaking_lesson_planner.storage import load_s9_state
from app.services.language_speaking_transition_gate.types import SpeakingStageTransitionDecision


class StaleSpeakingStageDecisionError(ValueError):
    """Submitted decision no longer matches locked authoritative state."""

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True, slots=True)
class SpeakingStagePersistResult:
    decision: SpeakingStageTransitionDecision
    snapshot: SpeakingStageSignalSnapshot
    stage_written: bool
    previous_stage: SpeakingLearningStage
    new_stage: SpeakingLearningStage


def _read_stage(row) -> SpeakingLearningStage:
    raw = getattr(row, "learning_stage_speaking", None)
    try:
        return SpeakingLearningStage(max(1, min(3, int(raw or 1))))
    except (TypeError, ValueError):
        return SpeakingLearningStage.foundation


def _official_from_row(row) -> str:
    val = getattr(row, "official_speaking_cefr", None)
    if val is None:
        return "A2"
    return val.value if hasattr(val, "value") else str(val or "A2")


def _build_snapshot_from_locked_row(
    row,
    *,
    student_id: int,
    language_id: int,
    official_cefr: str,
) -> SpeakingStageSignalSnapshot:
    payload = dict(row.promotion_readiness_json or {}) if row is not None else {}
    bucket = speaking_bucket_from_payload(payload)
    knowledge_model = knowledge_model_from_speaking_bucket(
        bucket, student_id=student_id, language_id=language_id
    )
    state = load_s9_state(bucket)
    return gather_speaking_stage_signals(
        official_cefr=official_cefr,
        current_stage=_read_stage(row),
        knowledge_model=knowledge_model,
        attempt_lineage=state.attempt_lineage,
    )


async def evaluate_and_persist_speaking_stage(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
    official_cefr: str | None = None,
) -> SpeakingStagePersistResult:
    """Evaluate gate under FOR UPDATE lock; write learning_stage_speaking if authorized."""
    # Lazy import avoids circular: learning_stage.__init__ ↔ transition_gate.policy
    from app.services.language_speaking_transition_gate.rules import evaluate_speaking_transition_gate

    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    row = await lock_speaking_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        # Should not happen after ensure; stay closed.
        empty = gather_speaking_stage_signals(
            official_cefr=(official_cefr or "A2").upper(),
            current_stage=SpeakingLearningStage.foundation,
            knowledge_model=None,
            attempt_lineage=None,
            refresh_retention=False,
        )
        decision = evaluate_speaking_transition_gate(empty)
        return SpeakingStagePersistResult(
            decision=decision,
            snapshot=empty,
            stage_written=False,
            previous_stage=SpeakingLearningStage.foundation,
            new_stage=SpeakingLearningStage.foundation,
        )

    row_cefr = _official_from_row(row).upper()
    if official_cefr is None:
        official_cefr = row_cefr
    else:
        official_cefr = str(official_cefr).upper()

    # Reject explicit cross-CEFR writes: row CEFR must match evaluation CEFR.
    if row_cefr != official_cefr:
        raise StaleSpeakingStageDecisionError(
            "stale_cefr",
            f"official_speaking_cefr mismatch: row={row_cefr} eval={official_cefr}",
        )

    previous = _read_stage(row)
    snapshot = _build_snapshot_from_locked_row(
        row, student_id=student_id, language_id=language_id, official_cefr=official_cefr
    )
    decision = evaluate_speaking_transition_gate(snapshot)

    if not (
        decision.authorized
        and decision.target_stage is not None
        and int(decision.target_stage) == int(previous) + 1
        and decision.current_stage == previous
    ):
        return SpeakingStagePersistResult(
            decision=decision,
            snapshot=snapshot,
            stage_written=False,
            previous_stage=previous,
            new_stage=previous,
        )

    # Sole mutation: learning_stage_speaking only. Never touch official_speaking_cefr.
    row.learning_stage_speaking = int(decision.target_stage)
    await db.flush()
    return SpeakingStagePersistResult(
        decision=decision,
        snapshot=snapshot,
        stage_written=True,
        previous_stage=previous,
        new_stage=decision.target_stage,
    )


async def apply_speaking_stage_transition(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
    submitted_decision: SpeakingStageTransitionDecision,
) -> SpeakingStagePersistResult:
    """Apply a previously computed decision only if still authorized on fresh evidence."""
    from app.services.language_speaking_transition_gate.rules import evaluate_speaking_transition_gate

    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    row = await lock_speaking_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        raise StaleSpeakingStageDecisionError("missing_progression_row")

    official_cefr = _official_from_row(row).upper()
    if submitted_decision.official_cefr.upper() != official_cefr:
        raise StaleSpeakingStageDecisionError("stale_cefr")

    snapshot = _build_snapshot_from_locked_row(
        row, student_id=student_id, language_id=language_id, official_cefr=official_cefr
    )
    if submitted_decision.signal_fingerprint != snapshot.snapshot_fingerprint:
        raise StaleSpeakingStageDecisionError("stale_evidence")
    if submitted_decision.current_stage != snapshot.current_stage:
        raise StaleSpeakingStageDecisionError("stale_stage")

    fresh = evaluate_speaking_transition_gate(snapshot)
    if not fresh.authorized:
        raise StaleSpeakingStageDecisionError("no_longer_eligible")

    previous = _read_stage(row)
    if previous != snapshot.current_stage:
        raise StaleSpeakingStageDecisionError("stale_stage")

    if fresh.target_stage is None or int(fresh.target_stage) != int(previous) + 1:
        raise StaleSpeakingStageDecisionError("invalid_target")

    # Idempotent: already at target → no-op.
    if int(previous) >= int(fresh.target_stage):
        return SpeakingStagePersistResult(
            decision=fresh,
            snapshot=snapshot,
            stage_written=False,
            previous_stage=previous,
            new_stage=previous,
        )

    row.learning_stage_speaking = int(fresh.target_stage)
    await db.flush()
    return SpeakingStagePersistResult(
        decision=fresh,
        snapshot=snapshot,
        stage_written=True,
        previous_stage=previous,
        new_stage=fresh.target_stage,
    )
