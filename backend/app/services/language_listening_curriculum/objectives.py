"""Objective progress and spaced review (Phase 2.3.1)."""

from __future__ import annotations

from app.services.language_cefr.engine import get_cefr_profile
from app.services.language_listening_curriculum.intent import LessonIntent
from app.services.language_listening_curriculum.objective_catalog import catalog_for_level
from app.services.language_listening_curriculum.skills import objective_slug
from app.services.language_listening_curriculum.types import CurriculumHistoryEntry, ObjectiveProgress, ObjectiveState

INTRODUCE_THRESHOLD = 1
PRACTICE_THRESHOLD = 3
MASTER_THRESHOLD = 5
REVIEW_INTERVAL = 12


def level_objectives(level: str) -> tuple[tuple[str, str], ...]:
    """Merge CEFR profile objectives with expanded catalog."""
    profile = get_cefr_profile(level)
    merged: dict[str, str] = {}
    for obj in profile.listening_objectives:
        slug = objective_slug(obj)
        merged[slug] = obj
    for oid, label, _skills in catalog_for_level(level):
        merged.setdefault(oid, label)
    return tuple((oid, merged[oid]) for oid in sorted(merged))


def build_objective_progress(
    history: list[CurriculumHistoryEntry],
    level: str,
) -> dict[str, ObjectiveProgress]:
    objectives = level_objectives(level)
    progress: dict[str, ObjectiveProgress] = {
        oid: ObjectiveProgress(objective_id=oid, label=label, state=ObjectiveState.introduced, exposure_count=0)
        for oid, label in objectives
    }

    for entry in history:
        for oid in entry.objectives:
            if oid not in progress:
                continue
            current = progress[oid]
            exposure = current.exposure_count + 1
            if exposure >= MASTER_THRESHOLD:
                state = ObjectiveState.mastered
            elif exposure >= PRACTICE_THRESHOLD:
                state = ObjectiveState.practicing
            elif exposure >= INTRODUCE_THRESHOLD:
                state = ObjectiveState.practicing
            else:
                state = ObjectiveState.introduced
            progress[oid] = ObjectiveProgress(
                objective_id=oid,
                label=current.label,
                state=state,
                exposure_count=exposure,
                last_seen_index=entry.generation_index,
            )
    return progress


def _review_due(progress: dict[str, ObjectiveProgress], generation_index: int) -> list[str]:
    due: list[tuple[int, str]] = []
    for oid, obj in progress.items():
        if obj.state == ObjectiveState.mastered and generation_index - obj.last_seen_index >= REVIEW_INTERVAL:
            due.append((obj.last_seen_index, oid))
    due.sort(key=lambda x: x[0])
    return [oid for _, oid in due]


def has_review_due(progress: dict[str, ObjectiveProgress], generation_index: int) -> bool:
    return bool(_review_due(progress, generation_index))


def objectives_for_lesson(
    progress: dict[str, ObjectiveProgress],
    *,
    generation_index: int,
    intent: LessonIntent,
    max_count: int = 2,
) -> tuple[tuple[str, ...], tuple[str, ...], bool]:
    """Return (focus objectives, review objectives, review_due_flag)."""
    review_due_list = _review_due(progress, generation_index)
    reviews = tuple(review_due_list[:1])

    under_practiced = sorted(
        [(obj.exposure_count, oid) for oid, obj in progress.items() if obj.state != ObjectiveState.mastered],
        key=lambda x: x[0],
    )
    unseen = [oid for oid, obj in progress.items() if obj.exposure_count == 0]

    def _rotated(ids: list[str], count: int) -> list[str]:
        if not ids:
            return []
        start = generation_index % len(ids)
        ordered = ids[start:] + ids[:start]
        return ordered[:count]

    focus: list[str] = []
    under_ids = [oid for _, oid in under_practiced]
    unseen_ids = sorted(unseen)

    if intent == LessonIntent.review and reviews:
        focus.append(reviews[0])
    elif intent == LessonIntent.exploration and unseen_ids:
        focus.extend(_rotated(unseen_ids, max_count))
    elif intent == LessonIntent.weak_recovery:
        focus.extend(_rotated(under_ids, max_count))
    else:
        focus.extend(_rotated(under_ids, max_count))

    if not focus and under_practiced:
        focus = [under_practiced[0][1]]
    if not focus and progress:
        focus = [next(iter(progress))]

    if reviews and reviews[0] not in focus and intent != LessonIntent.exploration:
        focus = focus[: max(1, max_count - 1)] + [reviews[0]]

    return tuple(focus[:max_count]), reviews, bool(review_due_list)


def review_priority_score(
    objectives: tuple[str, ...],
    progress: dict[str, ObjectiveProgress],
    generation_index: int,
) -> float:
    score = 0.0
    for oid in objectives:
        obj = progress.get(oid)
        if not obj:
            continue
        if obj.state == ObjectiveState.mastered and generation_index - obj.last_seen_index >= REVIEW_INTERVAL:
            score += 1.0
        elif obj.state == ObjectiveState.introduced:
            score += 0.6
        elif obj.state == ObjectiveState.practicing:
            score += 0.5
    return min(1.0, score / 2.0)
