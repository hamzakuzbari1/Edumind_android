"""Grammar Target Resolver — sole skill Runtime entry for grammar targets.

Skills must call this facade for current/candidate grammar_ids.
They must never read progression storage or invent curriculum IDs independently.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_grammar_catalog.catalog import get_default_catalog, get_topic
from app.services.language_grammar_integration.service import (
    resolve_targets as integration_resolve_targets,
)
from app.services.language_grammar_integration.service import (
    resolve_targets_from_snapshot as integration_resolve_from_snapshot,
)
from app.services.language_grammar_integration.types import (
    GrammarResolveTargetsRequest,
    GrammarResolveTargetsResult,
)
from app.services.language_grammar_target_resolver.types import (
    GrammarTargetMeta,
    GrammarTargetResolution,
    GrammarTargetResolveRequest,
)


def _meta_for(grammar_id: str) -> GrammarTargetMeta | None:
    topic = get_topic(grammar_id)
    if topic is None:
        return None
    return GrammarTargetMeta(
        grammar_id=topic.grammar_id,
        display_code=topic.display_code,
        display_name=topic.display_name,
        cefr_band=topic.cefr_band,
    )


def _enrich(
    request: GrammarTargetResolveRequest,
    inner: GrammarResolveTargetsResult,
) -> GrammarTargetResolution:
    catalog = get_default_catalog()
    metas: list[GrammarTargetMeta] = []
    for gid in inner.grammar_ids:
        meta = _meta_for(gid)
        if meta is not None:
            metas.append(meta)
    current_id = None
    if inner.progression is not None:
        candidate = inner.progression.current_grammar_id
        if candidate and candidate in catalog.topic_ids():
            current_id = candidate
    current_meta = _meta_for(current_id) if current_id else None
    return GrammarTargetResolution(
        grammar_ids=tuple(m.grammar_id for m in metas),
        display_codes=tuple(m.display_code for m in metas),
        topics=tuple(metas),
        current_grammar_id=current_id,
        current_display_code=current_meta.display_code if current_meta else None,
        anchor_cefr=inner.anchor_cefr,
        source_skill=request.source_skill,
    )


def resolve_from_snapshot(
    request: GrammarTargetResolveRequest,
    *,
    progression,
    mastery,
) -> GrammarTargetResolution:
    """Resolve targets from already-loaded progression/mastery snapshots.

    ``progression`` / ``mastery`` are opaque snapshots produced by Integration;
    skills should prefer ``resolve`` / ``GrammarTargetResolver.resolve``.
    """
    inner = integration_resolve_from_snapshot(
        GrammarResolveTargetsRequest(
            student_id=request.student_id,
            language_id=request.language_id,
            source_skill=request.source_skill,
            max_targets=request.max_targets,
            prefer_current=request.prefer_current,
        ),
        progression=progression,
        mastery=mastery,
    )
    return _enrich(request, inner)


async def resolve(
    db: AsyncSession,
    request: GrammarTargetResolveRequest,
) -> GrammarTargetResolution:
    """Skill-facing async resolve (read-only)."""
    inner = await integration_resolve_targets(
        db,
        GrammarResolveTargetsRequest(
            student_id=request.student_id,
            language_id=request.language_id,
            source_skill=request.source_skill,
            max_targets=request.max_targets,
            prefer_current=request.prefer_current,
        ),
    )
    return _enrich(request, inner)


class GrammarTargetResolver:
    """Named facade — skills depend on this package / surface only for targets."""

    @staticmethod
    def resolve_from_snapshot(
        request: GrammarTargetResolveRequest,
        *,
        progression,
        mastery,
    ) -> GrammarTargetResolution:
        return resolve_from_snapshot(request, progression=progression, mastery=mastery)

    @staticmethod
    async def resolve(db: AsyncSession, request: GrammarTargetResolveRequest) -> GrammarTargetResolution:
        return await resolve(db, request)
