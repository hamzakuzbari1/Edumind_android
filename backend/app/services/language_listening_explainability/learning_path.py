"""Listening journey / learning path builder (Phase 3.4)."""

from __future__ import annotations

from app.services.language_listening_confidence.telemetry import compute_confidence_telemetry
from app.services.language_listening_confidence.types import ConfidenceState
from app.services.language_listening_curriculum.objectives import level_objectives
from app.services.language_listening_explainability.types import (
    LearningPath,
    LearningPathObjective,
    ObjectivePathStatus,
)

JOURNEY_OBJECTIVE_IDS: tuple[str, ...] = (
    "main_idea",
    "detail",
    "inference",
    "purpose",
    "tone",
    "prediction",
    "opinion",
    "speaker_intention",
    "bias",
)


def _path_status(
    objective_id: str,
    *,
    confidence: float,
    mastery: float,
    exposure: int,
    is_mastered: bool,
    review_due: list[str],
) -> str:
    if is_mastered:
        return ObjectivePathStatus.mastered.value
    if objective_id in review_due:
        return ObjectivePathStatus.review.value
    if exposure == 0:
        return ObjectivePathStatus.not_started.value
    if confidence < 0.55:
        return ObjectivePathStatus.learning.value
    return ObjectivePathStatus.practicing.value


def _next_for_objective(
    objective_id: str,
    *,
    status: str,
    confidence: float,
    coverage: float,
    review_due: bool,
) -> str:
    if status == ObjectivePathStatus.mastered.value:
        return f"Maintain {slug_label(objective_id)} with periodic review."
    if review_due:
        return f"Schedule a review lesson targeting {slug_label(objective_id)}."
    if coverage < 0.55 and confidence >= 0.70:
        return (
            f"Practise {slug_label(objective_id)} across varied formats, topics, and speeds "
            f"(coverage {coverage:.2f})."
        )
    if confidence < 0.55:
        return f"Prioritise lessons with skill focus including {slug_label(objective_id)}."
    return f"Continue practising {slug_label(objective_id)} at current challenge band."


def slug_label(slug: str) -> str:
    return slug.replace("_", " ")


def build_learning_path(
    confidence_state: ConfidenceState | None,
    *,
    level: str,
) -> LearningPath:
    labels = {oid: label for oid, label in level_objectives(level)}
    telemetry = compute_confidence_telemetry(confidence_state) if confidence_state else None
    review_due = list(telemetry.review_due) if telemetry else []

    entries: list[LearningPathObjective] = []
    for oid in JOURNEY_OBJECTIVE_IDS:
        if oid not in labels:
            continue
        rec = confidence_state.objectives.get(oid) if confidence_state else None
        if rec is None:
            entries.append(
                LearningPathObjective(
                    objective_id=oid,
                    label=labels[oid],
                    confidence=0.35,
                    coverage=0.0,
                    mastery=0.0,
                    status=ObjectivePathStatus.not_started.value,
                    next_recommendation=f"Introduce {slug_label(oid)} in an upcoming lesson.",
                )
            )
            continue

        status = _path_status(
            oid,
            confidence=rec.confidence,
            mastery=rec.mastery_score,
            exposure=rec.exposure_count,
            is_mastered=rec.is_mastered,
            review_due=review_due,
        )
        entries.append(
            LearningPathObjective(
                objective_id=oid,
                label=labels[oid],
                confidence=rec.confidence,
                coverage=rec.coverage_score,
                mastery=rec.mastery_score,
                status=status,
                next_recommendation=_next_for_objective(
                    oid,
                    status=status,
                    confidence=rec.confidence,
                    coverage=rec.coverage_score,
                    review_due=oid in review_due,
                ),
            )
        )

    return LearningPath(
        level=level,
        journey_title="Listening Journey",
        objectives=tuple(entries),
    )
