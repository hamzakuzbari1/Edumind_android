"""Writing promotion readiness — continuous 0–100 score; never promotes CEFR."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.services.language_progression_service import ensure_progression_row, get_official_cefr, record_progression_event
from app.services.language_promotion_readiness.types import (
    PromotionReadinessResult,
    PromotionReadinessTelemetry,
    ReadinessDimensionScore,
    ReadinessStatus,
)
from app.services.language_writing_learning_stage.engine import evaluate_writing_learning_stage
from app.services.language_writing_learning_stage.scoring import compute_writing_stage_score
from app.services.language_writing_learning_stage.signals import gather_writing_signals
from app.services.language_writing_learning_stage.types import WritingLearningStage
from app.services.language_writing_progression.storage import WRITING_PROGRESSION_KEY
from app.services.language_writing_transition_gate.rules import GATE_THRESHOLDS, evaluate_writing_transition_gate

WRITING_READINESS_WEIGHTS: dict[str, float] = {
    "learning_stage": 0.10,
    "stage_score": 0.08,
    "transition_gate": 0.16,
    "grammar_mastery": 0.10,
    "vocabulary_mastery": 0.08,
    "task_response": 0.12,
    "organization": 0.06,
    "cefr_alignment": 0.08,
    "revision_quality": 0.08,
    "confidence": 0.06,
    "evidence": 0.06,
    "stability": 0.02,
}


def estimated_lessons_from_readiness(estimated_remaining: float) -> int:
    """Canonical mapping from readiness gap (0–100) to lessons-remaining estimate.

    Single source of truth so the journey builder and readiness persistence agree.
    """
    return max(1, int(round(float(estimated_remaining) / 12)))


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _ratio(current: float, required: float) -> float:
    if required <= 0:
        return 1.0
    return _clamp01(current / required)


def _status(score: int) -> ReadinessStatus:
    if score >= 100:
        return ReadinessStatus.PROMOTION_AVAILABLE
    if score >= 80:
        return ReadinessStatus.READY
    if score >= 50:
        return ReadinessStatus.ALMOST_READY
    return ReadinessStatus.NOT_READY


def evaluate_writing_readiness_from_signals(
    *,
    official_cefr: str,
    persistent_stage: int,
    snapshot,
    gate,
    stage_score: int,
) -> PromotionReadinessResult:
    bar = GATE_THRESHOLDS[(int(WritingLearningStage.intermediate), int(WritingLearningStage.advanced))]
    stage_progress = (persistent_stage - 1) / 2.0
    gate_progress = gate.overall_gate_score / 100.0

    raw = [
        ("learning_stage", stage_progress, 1.0),
        ("stage_score", stage_score / 100.0, bar.min_stage_score / 100.0),
        ("transition_gate", gate_progress, 1.0),
        ("grammar_mastery", snapshot.grammar_mastery_avg, bar.min_grammar),
        ("vocabulary_mastery", snapshot.vocabulary_mastery_avg, bar.min_vocabulary),
        ("task_response", snapshot.task_response_avg, bar.min_task_response),
        ("organization", snapshot.organization_avg, bar.min_stability),
        ("cefr_alignment", snapshot.cefr_alignment_avg, bar.min_cefr_alignment),
        ("revision_quality", snapshot.revision_quality_avg, bar.min_revision),
        ("confidence", snapshot.confidence_avg, bar.min_confidence),
        ("evidence", snapshot.evidence_coverage_avg, bar.min_evidence),
        ("stability", snapshot.recent_stability, bar.min_stability),
    ]
    dims: list[ReadinessDimensionScore] = []
    for name, current, required in raw:
        if name in {"learning_stage", "transition_gate"}:
            progress = _clamp01(current)
        else:
            progress = _ratio(current, required)
        w = WRITING_READINESS_WEIGHTS[name]
        dims.append(
            ReadinessDimensionScore(
                name=name,
                current=round(current, 4),
                required=round(required, 4),
                progress=round(progress, 4),
                weight=w,
                contribution=round(progress * w * 100.0, 2),
            )
        )
    score = int(max(0, min(100, round(sum(d.contribution for d in dims)))))
    status = _status(score)
    gaps = sorted(
        ((d.name, (1.0 - d.progress) * d.weight) for d in dims if d.progress < 0.99),
        key=lambda x: x[1],
        reverse=True,
    )
    primary = tuple(_blocker_label(n) for n, _ in gaps[:2])
    secondary = tuple(_blocker_label(n) for n, _ in gaps[2:4])
    strengths: list[str] = []
    if snapshot.grammar_mastery_avg >= bar.min_grammar:
        strengths.append("Grammar mastery is on track for promotion.")
    if snapshot.revision_quality_avg >= bar.min_revision:
        strengths.append("Revision quality shows consistent improvement.")
    if gate.eligible:
        strengths.append("All stage transition requirements are currently met.")

    return PromotionReadinessResult(
        official_cefr=official_cefr.upper(),
        readiness_score=score,
        status=status,
        estimated_remaining=round(max(0.0, 100.0 - score), 1),
        primary_blockers=primary,
        secondary_blockers=secondary,
        strengths=tuple(strengths[:4]),
        next_actions=tuple(
            f"Improve {_blocker_label(n).lower()}."
            for n, _ in gaps[:3]
        ),
        telemetry=PromotionReadinessTelemetry(
            official_cefr=official_cefr.upper(),
            persistent_stage=persistent_stage,
            stage_score=stage_score,
            gate_overall_score=gate.overall_gate_score,
            gate_eligible=gate.eligible,
            dimension_scores=tuple(dims),
            skill="writing",
        ),
    )


def _blocker_label(name: str) -> str:
    return {
        "learning_stage": "Learning stage",
        "stage_score": "Stage score",
        "transition_gate": "Stage transition gate",
        "grammar_mastery": "Grammar mastery",
        "vocabulary_mastery": "Vocabulary mastery",
        "task_response": "Task response",
        "organization": "Organization & coherence",
        "cefr_alignment": "CEFR-level alignment",
        "revision_quality": "Revision quality",
        "confidence": "Writing confidence",
        "evidence": "Evidence coverage",
        "stability": "Performance stability",
    }.get(name, name.replace("_", " ").title())


async def evaluate_writing_promotion_readiness(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    official_cefr: str | None = None,
) -> PromotionReadinessResult:
    if official_cefr is None:
        official = await get_official_cefr(db, student_id=student_id, language_id=language_id, skill="writing")
        official_cefr = official.level.value
    stage_result = await evaluate_writing_learning_stage(
        db, student_id=student_id, language_id=language_id, official_cefr=official_cefr
    )
    row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    payload = dict(row.promotion_readiness_json or {}) if row else {}
    snapshot = gather_writing_signals(payload, official_cefr=official_cefr)
    stage_score = compute_writing_stage_score(snapshot)
    gate = evaluate_writing_transition_gate(
        persistent_stage=int(stage_result.current_stage),
        stage_score=stage_score,
        snapshot=snapshot,
    )
    return evaluate_writing_readiness_from_signals(
        official_cefr=official_cefr,
        persistent_stage=int(stage_result.current_stage),
        snapshot=snapshot,
        gate=gate,
        stage_score=stage_score,
    )


async def evaluate_and_persist_writing_promotion_readiness(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    official_cefr: str | None = None,
) -> PromotionReadinessResult:
    result = await evaluate_writing_promotion_readiness(
        db, student_id=student_id, language_id=language_id, official_cefr=official_cefr
    )
    row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        return result
    payload = dict(row.promotion_readiness_json or {})
    payload["writing_readiness"] = {
        "skill": "writing",
        "official_cefr": result.official_cefr,
        "readiness_score": result.readiness_score,
        "status": result.status.value,
        "estimated_remaining": result.estimated_remaining,
        "primary_blockers": list(result.primary_blockers),
        "secondary_blockers": list(result.secondary_blockers),
        "persistent_stage": result.telemetry.persistent_stage,
        "stage_score": result.telemetry.stage_score,
        "gate_overall_score": result.telemetry.gate_overall_score,
        "gate_eligible": result.telemetry.gate_eligible,
    }
    writing = dict(payload.get(WRITING_PROGRESSION_KEY) or {})
    writing["estimated_lessons_to_next_stage"] = estimated_lessons_from_readiness(result.estimated_remaining)
    payload[WRITING_PROGRESSION_KEY] = writing
    row.promotion_readiness_json = payload
    row.promotion_readiness_score = result.readiness_score
    flag_modified(row, "promotion_readiness_json")
    await db.flush()
    await record_progression_event(
        db,
        student_id=student_id,
        language_id=language_id,
        event_type="writing_promotion_readiness_updated",
        payload_json={"readiness_score": result.readiness_score, "status": result.status.value},
        force=True,
    )
    return result
