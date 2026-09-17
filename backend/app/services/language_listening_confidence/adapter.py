"""Bridge confidence state to curriculum ObjectiveProgress (Phase 3.2)."""

from __future__ import annotations

from app.services.language_listening_confidence.constants import MASTERY_SCORE_THRESHOLD
from app.services.language_listening_confidence.types import ConfidenceState
from app.services.language_listening_curriculum.objectives import level_objectives
from app.services.language_listening_curriculum.types import ObjectiveProgress, ObjectiveState


def confidence_to_objective_progress(state: ConfidenceState) -> dict[str, ObjectiveProgress]:
    """Synthetic ObjectiveProgress for curriculum scoring — derived from confidence, not exposure."""
    progress: dict[str, ObjectiveProgress] = {}
    for oid, label in level_objectives(state.level):
        rec = state.objectives.get(oid)
        if rec is None:
            progress[oid] = ObjectiveProgress(
                objective_id=oid,
                label=label,
                state=ObjectiveState.introduced,
                exposure_count=0,
                last_seen_index=-1,
            )
            continue
        if rec.is_mastered:
            obj_state = ObjectiveState.mastered
        elif rec.mastery_score >= MASTERY_SCORE_THRESHOLD * 0.65 or rec.confidence >= 0.55:
            obj_state = ObjectiveState.practicing
        else:
            obj_state = ObjectiveState.introduced
        progress[oid] = ObjectiveProgress(
            objective_id=oid,
            label=label,
            state=obj_state,
            exposure_count=rec.exposure_count,
            last_seen_index=rec.last_update_index,
        )
    return progress


def mastered_objectives(state: ConfidenceState) -> list[str]:
    return [oid for oid, rec in state.objectives.items() if rec.is_mastered]


def under_confident_objectives(state: ConfidenceState, *, threshold: float = 0.55) -> list[str]:
    return [oid for oid, rec in state.objectives.items() if rec.confidence < threshold]
