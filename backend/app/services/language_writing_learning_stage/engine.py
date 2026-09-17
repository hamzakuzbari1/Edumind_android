"""Writing learning stage engine — gate-gated stage transitions."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.services.language_progression_service import ensure_progression_row, get_official_cefr
from app.services.language_writing_learning_stage.scoring import compute_writing_stage_score, score_to_band
from app.services.language_writing_learning_stage.signals import gather_writing_signals
from app.services.language_writing_learning_stage.types import (
    WritingLearningStage,
    WritingLearningStageResult,
    writing_stage_label,
)
from app.services.language_writing_progression.storage import WRITING_PROGRESSION_KEY, writing_state_from_payload
from app.services.language_writing_transition_gate.rules import evaluate_writing_transition_gate


async def load_writing_stage(db: AsyncSession, *, student_id: int, language_id: int) -> int:
    row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        return 1
    if row.learning_stage_writing:
        return max(1, min(3, int(row.learning_stage_writing)))
    state = writing_state_from_payload(dict(row.promotion_readiness_json or {}))
    return max(1, min(3, int(state.get("learning_stage") or 1)))


async def evaluate_writing_learning_stage(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    official_cefr: str | None = None,
) -> WritingLearningStageResult:
    if official_cefr is None:
        official = await get_official_cefr(db, student_id=student_id, language_id=language_id, skill="writing")
        official_cefr = official.level.value
    row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    payload = dict(row.promotion_readiness_json or {}) if row else {}
    persistent = await load_writing_stage(db, student_id=student_id, language_id=language_id)
    snapshot = gather_writing_signals(payload, official_cefr=official_cefr)
    stage_score = compute_writing_stage_score(snapshot)
    gate = evaluate_writing_transition_gate(
        persistent_stage=persistent,
        stage_score=stage_score,
        snapshot=snapshot,
    )
    current = WritingLearningStage(persistent)
    return WritingLearningStageResult(
        official_cefr=official_cefr.upper(),
        current_stage=current,
        stage_score=stage_score,
        stage_band=score_to_band(stage_score),
        eligible_for_next_stage=gate.eligible,
        next_stage=gate.next_stage if gate.eligible else None,
        progress_to_next=gate.estimated_remaining_progress,
        primary_blocker=gate.primary_blocker,
        grammar_mastery_avg=snapshot.grammar_mastery_avg,
        vocabulary_mastery_avg=snapshot.vocabulary_mastery_avg,
        revision_quality_avg=snapshot.revision_quality_avg,
        confidence_avg=snapshot.confidence_avg,
        evidence_coverage_avg=snapshot.evidence_coverage_avg,
        stability_avg=snapshot.recent_stability,
        lesson_index=snapshot.lesson_index,
    )


async def evaluate_and_persist_writing_stage(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    official_cefr: str | None = None,
) -> WritingLearningStageResult:
    result = await evaluate_writing_learning_stage(
        db, student_id=student_id, language_id=language_id, official_cefr=official_cefr
    )
    if not (
        result.eligible_for_next_stage
        and result.next_stage is not None
        and result.next_stage == int(result.current_stage) + 1
    ):
        return result

    row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        return result
    payload = dict(row.promotion_readiness_json or {})
    writing = writing_state_from_payload(payload)
    writing["learning_stage"] = result.next_stage
    writing["learning_stage_label"] = writing_stage_label(
        official_cefr=result.official_cefr,
        stage=WritingLearningStage(result.next_stage),
    )
    writing["stage_advanced_at"] = datetime.now(timezone.utc).isoformat()
    payload[WRITING_PROGRESSION_KEY] = writing
    row.promotion_readiness_json = payload
    row.learning_stage_writing = result.next_stage
    flag_modified(row, "promotion_readiness_json")
    await db.flush()
    return await evaluate_writing_learning_stage(
        db, student_id=student_id, language_id=language_id, official_cefr=result.official_cefr
    )
