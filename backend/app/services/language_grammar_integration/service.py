"""Grammar Integration Service (G3.1) — sole facade for Planner / skill read models."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.enums import LanguageLevel
from app.services.language_grammar.enums import GrammarCEFRBand
from app.services.language_grammar_catalog.catalog import get_default_catalog
from app.services.language_grammar_catalog.types import GrammarCatalogSnapshot, GrammarTopic
from app.services.language_grammar_integration.types import (
    GrammarCompletedSyncResult,
    GrammarLearningSnapshot,
    GrammarMasteryPlanSummary,
    GrammarResolveTargetsRequest,
    GrammarResolveTargetsResult,
    GrammarReviewPlanItem,
    GrammarTopicPlanMeta,
)
from app.services.language_grammar_mastery.service import (
    completion_ready_ids,
    get_grammar_mastery_snapshot,
    public_views,
)
from app.services.language_grammar_mastery.types import (
    GrammarMasterySnapshot,
    PublicGrammarMasteryView,
)
from app.services.language_grammar_progression.service import (
    get_grammar_progression_snapshot,
    record_grammar_topic_completed,
    selection_snapshot_or_disabled,
)
from app.services.language_grammar_progression.storage import (
    progression_bucket_from_payload,
    student_state_from_bucket,
)
from app.services.language_grammar_progression.types import (
    GrammarProgressionSnapshot,
    GrammarProgressionStudentState,
)
from app.services.language_grammar_review.engine import format_ts
from app.services.language_grammar_review.service import (
    compute_from_mastery,
    evaluate_review_queue,
)
from app.services.language_grammar_review.types import GrammarReviewSnapshot
from app.services.language_progression_service import (
    ensure_progression_row,
    get_official_overall_cefr,
)


def _level_to_band(level: LanguageLevel | str | GrammarCEFRBand) -> GrammarCEFRBand:
    if isinstance(level, GrammarCEFRBand):
        return level
    value = level.value if isinstance(level, LanguageLevel) else str(level)
    return GrammarCEFRBand(value.upper())


def _topic_meta(topic: GrammarTopic) -> GrammarTopicPlanMeta:
    req = topic.evidence_requirements
    return GrammarTopicPlanMeta(
        grammar_id=topic.grammar_id,
        display_name=topic.display_name,
        cefr_band=topic.cefr_band,
        learning_objectives=tuple(topic.learning_objectives),
        best_reinforcement_skills=tuple(topic.best_reinforcement_skills),
        recommended_contexts=tuple(topic.recommended_contexts),
        minimum_context_diversity=int(topic.minimum_context_diversity),
        mastery_threshold=float(topic.mastery_threshold),
        focus_note=str(topic.focus_note or ""),
        evidence_min_observations=int(req.min_observations),
        evidence_min_contexts=int(req.min_distinct_contexts),
        evidence_min_skills=int(req.min_skills_covered),
    )


def _mastery_summaries(views: tuple[PublicGrammarMasteryView, ...]) -> tuple[GrammarMasteryPlanSummary, ...]:
    return tuple(
        GrammarMasteryPlanSummary(
            grammar_id=v.grammar_id,
            overall_mastery=float(v.overall_mastery),
            state=v.state,
            evidence_count=int(v.evidence_count),
            distinct_context_count=int(v.distinct_context_count),
            last_seen_at=v.last_seen_at,
        )
        for v in views
    )


def _review_items(review: GrammarReviewSnapshot) -> tuple[GrammarReviewPlanItem, ...]:
    return tuple(
        GrammarReviewPlanItem(
            grammar_id=item.grammar_id,
            due_at=item.due_at,
            priority=item.priority,
            reason=item.reason,
            recommended_review_mode=item.recommended_review_mode,
            review_due=bool(item.review_due),
            urgency_score=float(item.urgency_score),
        )
        for item in review.queue.items
    )


def build_learning_snapshot(
    *,
    student_id: int,
    language_id: int,
    overall_cefr: GrammarCEFRBand | LanguageLevel | str,
    progression: GrammarProgressionSnapshot,
    mastery: GrammarMasterySnapshot,
    review: GrammarReviewSnapshot,
    catalog: GrammarCatalogSnapshot | None = None,
    as_of: str | None = None,
    fatigue_budget_minutes: int = 45,
) -> GrammarLearningSnapshot:
    """Pure facade assembly — Planner never calls engines directly."""
    cat = catalog or get_default_catalog()
    band = _level_to_band(overall_cefr)
    # Learning snapshot is for Grammar Planner — use authoritative current/next
    # (SELECT gate applies to skill resolve_targets, not to Grammar lessons).
    current_id = progression.current_grammar_id
    next_id = progression.next_grammar_id
    current_topic = _topic_meta(cat.topic_by_id(current_id)) if current_id and cat.topic_by_id(current_id) else None
    next_topic = _topic_meta(cat.topic_by_id(next_id)) if next_id and cat.topic_by_id(next_id) else None

    index: dict[str, GrammarTopicPlanMeta] = {}
    for topic in cat.topics:
        index[topic.grammar_id] = _topic_meta(topic)
    # Ensure review/current topics present
    for gid in [current_id, next_id, *[i.grammar_id for i in review.queue.items]]:
        if gid and gid not in index and cat.topic_by_id(gid):
            index[gid] = _topic_meta(cat.topic_by_id(gid))  # type: ignore[arg-type]

    as_of_value = as_of or review.as_of or format_ts(datetime.now(timezone.utc))
    # Review-off => empty queue, not a disabled learning snapshot / planner.
    enabled = bool(progression.enabled and mastery.enabled and bool(cat.topics))
    review_queue = _review_items(review) if review.enabled else ()

    return GrammarLearningSnapshot(
        student_id=student_id,
        language_id=language_id,
        overall_cefr=band,
        current_grammar_id=current_id,
        next_grammar_id=next_id,
        current_topic=current_topic,
        next_topic=next_topic,
        mastery_summaries=_mastery_summaries(public_views(mastery)),
        review_queue=review_queue,
        catalog_version=str(cat.version),
        catalog_schema_version=int(cat.schema_version),
        fatigue_budget_minutes=max(10, int(fatigue_budget_minutes)),
        as_of=as_of_value,
        enabled=enabled,
        topic_index=index,
    )


def sync_completed_topics(
    *,
    mastery: GrammarMasterySnapshot,
    student: GrammarProgressionStudentState,
) -> GrammarCompletedSyncResult:
    """Compute which mastered topics should sync into Progression completed_ids (pure)."""
    ready = frozenset(completion_ready_ids(mastery))
    already = frozenset(student.completed_ids)
    synced = tuple(sorted(ready - already))
    return GrammarCompletedSyncResult(
        synced_ids=synced,
        already_completed=tuple(sorted(ready & already)),
    )


def resolve_targets_from_snapshot(
    request: GrammarResolveTargetsRequest,
    *,
    progression: GrammarProgressionSnapshot,
    mastery: GrammarMasterySnapshot,
) -> GrammarResolveTargetsResult:
    """G0 skill resolve_targets using progression + public mastery (no writes)."""
    selection = selection_snapshot_or_disabled(progression)
    ids: list[str] = []
    if request.prefer_current and selection.current_grammar_id:
        ids.append(selection.current_grammar_id)
    for gid in selection.candidate_pool_ids:
        if gid not in ids:
            ids.append(gid)
        if len(ids) >= max(1, int(request.max_targets)):
            break
    return GrammarResolveTargetsResult(
        grammar_ids=tuple(ids[: max(1, int(request.max_targets))]),
        anchor_cefr=selection.anchor_cefr,
        progression=selection,
        public_mastery=public_views(mastery, for_selection=True),
    )


async def build_learning_snapshot_async(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
    as_of: str | None = None,
    fatigue_budget_minutes: int = 45,
) -> GrammarLearningSnapshot:
    """Load engines via facade and assemble GrammarLearningSnapshot."""
    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    overall = await get_official_overall_cefr(db, student_id=student_id, language_id=language_id)
    band = _level_to_band(overall.level)

    progression = await get_grammar_progression_snapshot(
        db, student_id=student_id, language_id=language_id
    )
    mastery = await get_grammar_mastery_snapshot(
        db, student_id=student_id, language_id=language_id
    )
    review = await evaluate_review_queue(
        db, student_id=student_id, language_id=language_id, as_of=as_of
    )
    return build_learning_snapshot(
        student_id=student_id,
        language_id=language_id,
        overall_cefr=band,
        progression=progression,
        mastery=mastery,
        review=review,
        as_of=as_of,
        fatigue_budget_minutes=fatigue_budget_minutes,
    )


async def sync_completed_topics_async(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
) -> GrammarCompletedSyncResult:
    """Persist Mastery mastered → Progression completed_ids (facade-owned sync)."""
    mastery = await get_grammar_mastery_snapshot(
        db, student_id=student_id, language_id=language_id
    )
    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    from app.services.language_grammar_progression.locking import lock_grammar_progression_row

    row = await lock_grammar_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        return GrammarCompletedSyncResult()

    student = student_state_from_bucket(
        progression_bucket_from_payload(dict(row.promotion_readiness_json or {})),
        student_id=student_id,
        language_id=language_id,
    )
    plan = sync_completed_topics(mastery=mastery, student=student)
    for gid in plan.synced_ids:
        await record_grammar_topic_completed(
            db, student_id=student_id, language_id=language_id, grammar_id=gid
        )
    return plan


async def resolve_targets(
    db: AsyncSession,
    request: GrammarResolveTargetsRequest,
) -> GrammarResolveTargetsResult:
    """Skill-facing resolve_targets (read-only — Wave D: no locks / no unlock writes)."""
    progression = await get_grammar_progression_snapshot(
        db,
        student_id=request.student_id,
        language_id=request.language_id,
        for_selection=True,
    )
    mastery = await get_grammar_mastery_snapshot(
        db, student_id=request.student_id, language_id=request.language_id
    )
    return resolve_targets_from_snapshot(request, progression=progression, mastery=mastery)


class GrammarIntegrationService:
    """Named facade class — Planner depends on this package / surface only."""

    @staticmethod
    def build_learning_snapshot(**kwargs) -> GrammarLearningSnapshot:
        return build_learning_snapshot(**kwargs)

    @staticmethod
    def sync_completed_topics(**kwargs) -> GrammarCompletedSyncResult:
        return sync_completed_topics(**kwargs)

    @staticmethod
    def resolve_targets_from_snapshot(
        request: GrammarResolveTargetsRequest,
        *,
        progression: GrammarProgressionSnapshot,
        mastery: GrammarMasterySnapshot,
    ) -> GrammarResolveTargetsResult:
        return resolve_targets_from_snapshot(request, progression=progression, mastery=mastery)

    @staticmethod
    def build_learning_snapshot_for_planner(**kwargs) -> GrammarLearningSnapshot:
        return build_learning_snapshot_for_planner(**kwargs)

    @staticmethod
    async def build_learning_snapshot_async(db: AsyncSession, **kwargs) -> GrammarLearningSnapshot:
        return await build_learning_snapshot_async(db, **kwargs)

    @staticmethod
    async def sync_completed_topics_async(db: AsyncSession, **kwargs) -> GrammarCompletedSyncResult:
        return await sync_completed_topics_async(db, **kwargs)

    @staticmethod
    async def resolve_targets(
        db: AsyncSession, request: GrammarResolveTargetsRequest
    ) -> GrammarResolveTargetsResult:
        return await resolve_targets(db, request)


# Convenience: pure path when callers already have engine outputs + CEFR
def build_learning_snapshot_for_planner(
    *,
    student_id: int,
    language_id: int,
    overall_cefr: GrammarCEFRBand | LanguageLevel | str,
    progression: GrammarProgressionSnapshot,
    mastery: GrammarMasterySnapshot,
    as_of: str,
    fatigue_budget_minutes: int = 45,
) -> GrammarLearningSnapshot:
    """Assemble snapshot including a computed review queue from mastery."""
    from app.services.language_grammar_review.engine import empty_student_state

    review = compute_from_mastery(
        mastery=mastery,
        student=empty_student_state(student_id=student_id, language_id=language_id),
        as_of=as_of,
    )
    return build_learning_snapshot(
        student_id=student_id,
        language_id=language_id,
        overall_cefr=overall_cefr,
        progression=progression,
        mastery=mastery,
        review=review,
        as_of=as_of,
        fatigue_budget_minutes=fatigue_budget_minutes,
    )
