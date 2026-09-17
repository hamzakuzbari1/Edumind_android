"""Listening signal gathering for learning stage and transition gate (Phase 5.1 / 5.2)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_learning_stage.types import ListeningSignalSnapshot
from app.services.language_listening_challenge.scoring import compute_challenge_score
from app.services.language_listening_challenge.storage import load_student_challenge
from app.services.language_listening_confidence.storage import load_student_confidence
from app.services.language_listening_confidence.telemetry import compute_confidence_telemetry
from app.services.language_listening_curriculum.engine import _curriculum_stage
from app.services.language_listening_curriculum.history import load_curriculum_history
from app.services.language_listening_curriculum.objectives import build_objective_progress
from app.services.language_listening_curriculum.types import ObjectiveState


def _curriculum_progression_score(stage: str) -> float:
    return {"exploring": 0.25, "developing": 0.55, "consolidating": 0.85}.get(stage, 0.35)


def _review_completion_ratio(challenge_state) -> float:
    window = challenge_state.history[-10:]
    if not window:
        return 0.5
    reviews = [rec for rec in window if rec.was_review]
    if not reviews:
        return sum(rec.accuracy for rec in window) / len(window)
    return sum(rec.review_performance for rec in reviews) / len(reviews)


def _recent_stability(challenge_state, confidence_state) -> float:
    window = challenge_state.history[-8:]
    if len(window) >= 3:
        scores = [rec.lesson_score for rec in window]
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        stability = 1.0 - min(1.0, variance * 4.0)
        return max(0.0, min(1.0, stability))
    trends = [rec.trend for rec in confidence_state.objectives.values()]
    if not trends:
        return 0.5
    avg_trend = sum(trends) / len(trends)
    return max(0.0, min(1.0, 0.5 + avg_trend))


def _detect_missing_evidence_flags(
    *,
    needs_evidence: list[str],
    missing_evidence_summary: dict[str, dict[str, object]],
) -> tuple[bool, bool]:
    missing_speaker = False
    missing_inference = False
    for oid in needs_evidence:
        summary = missing_evidence_summary.get(oid) or {}
        speakers = summary.get("speakers") or summary.get("speaker") or []
        if isinstance(speakers, (list, tuple)) and speakers:
            missing_speaker = True
        label = str(summary.get("label") or oid).lower()
        if "infer" in label or "inference" in label:
            missing_inference = True
        dims = summary.get("missing") or summary.get("missing_axes") or []
        if isinstance(dims, (list, tuple)):
            if any("speaker" in str(d).lower() for d in dims):
                missing_speaker = True
            if any("infer" in str(d).lower() for d in dims):
                missing_inference = True
    return missing_speaker, missing_inference


async def gather_listening_signals(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    official_cefr: str,
) -> ListeningSignalSnapshot:
    """Collect listening-only signals from Confidence, Evidence, Challenge, Curriculum."""
    level = official_cefr.upper()
    confidence_state = await load_student_confidence(
        db, student_id=student_id, language_id=language_id, level=level
    )
    challenge_state = await load_student_challenge(
        db, student_id=student_id, language_id=language_id, level=level
    )
    curriculum_history = await load_curriculum_history(
        db, language_id=language_id, level=level, student_id=student_id
    )

    conf_telemetry = compute_confidence_telemetry(confidence_state)
    objective_progress = build_objective_progress(curriculum_history, level)
    total_objectives = len(objective_progress)
    mastered = sum(1 for p in objective_progress.values() if p.state == ObjectiveState.mastered)
    mastery_ratio = mastered / total_objectives if total_objectives else 0.0

    curriculum_stage = _curriculum_stage(objective_progress)
    needs_evidence = tuple(conf_telemetry.needs_evidence[:8])
    review_due = tuple(conf_telemetry.review_due[:8])
    missing_speaker, missing_inference = _detect_missing_evidence_flags(
        needs_evidence=list(needs_evidence),
        missing_evidence_summary=conf_telemetry.missing_evidence_summary,
    )

    return ListeningSignalSnapshot(
        official_cefr=level,
        confidence_avg=conf_telemetry.average_confidence,
        confidence_mastery_avg=conf_telemetry.average_mastery_score,
        evidence_coverage_avg=conf_telemetry.average_coverage,
        challenge_score=compute_challenge_score(challenge_state, confidence_state),
        curriculum_progression=_curriculum_progression_score(curriculum_stage),
        objective_mastery_ratio=mastery_ratio,
        review_completion_ratio=_review_completion_ratio(challenge_state),
        recent_stability=_recent_stability(challenge_state, confidence_state),
        lesson_index=confidence_state.lesson_index,
        mastered_objectives=mastered,
        total_objectives=total_objectives,
        challenge_level=str(challenge_state.current_level.value),
        demote_streak=challenge_state.demote_streak,
        pending_review_count=len(conf_telemetry.review_due),
        review_due_objectives=review_due,
        needs_evidence_objectives=needs_evidence,
        missing_speaker_evidence=missing_speaker,
        missing_inference_evidence=missing_inference,
    )
