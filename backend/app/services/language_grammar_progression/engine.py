"""Pure Grammar Progression decision engine (G2.1 + patch).

No DB. No LLM. No randomness. No mastery/review/planner imports.
"""

from __future__ import annotations

from app.services.language_grammar.enums import GrammarCandidatePriority, GrammarCEFRBand
from app.services.language_grammar.id_canon import assert_canonical_grammar_id, normalize_grammar_id
from app.services.language_grammar_catalog.cefr_order import CEFR_SEQUENCE, cefr_rank
from app.services.language_grammar_catalog.types import GrammarCatalogSnapshot, GrammarTopic
from app.services.language_grammar_progression.types import (
    STRETCH_EARLY_TOPIC_LIMIT,
    GrammarCandidatePriorityEntry,
    GrammarProgressionSnapshot,
    GrammarProgressionStudentState,
)


class GrammarProgressionError(ValueError):
    """Invalid progression input or catalog inconsistency."""


_PRIORITY_RANK = {
    GrammarCandidatePriority.primary: 0,
    GrammarCandidatePriority.secondary: 1,
    GrammarCandidatePriority.optional: 2,
    GrammarCandidatePriority.stretch: 3,
}


def _sorted_unique(ids: frozenset[str] | set[str] | tuple[str, ...], order_index: dict[str, int]) -> tuple[str, ...]:
    return tuple(sorted(ids, key=lambda gid: (order_index.get(gid, 10**9), gid)))


def _next_band(anchor: GrammarCEFRBand) -> GrammarCEFRBand | None:
    rank = cefr_rank(anchor)
    for band in CEFR_SEQUENCE:
        if cefr_rank(band) == rank + 1:
            return band
    return None


def _validate_student_ids(
    student: GrammarProgressionStudentState,
    catalog_ids: frozenset[str],
) -> None:
    for gid in student.completed_ids | student.unlocked_ids:
        if gid not in catalog_ids:
            raise GrammarProgressionError(f"Unknown grammar_id in student snapshot: {gid}")
        assert_canonical_grammar_id(gid)
    if student.current_grammar_id:
        cur = normalize_grammar_id(student.current_grammar_id)
        if cur not in catalog_ids:
            raise GrammarProgressionError(f"Unknown current grammar_id: {cur}")


def _build_candidate_pool(
    topics: tuple[GrammarTopic, ...],
    anchor: GrammarCEFRBand,
) -> tuple[str, ...]:
    eligible = [t for t in topics if cefr_rank(t.cefr_band) <= cefr_rank(anchor)]
    eligible.sort(key=lambda t: (t.introduction_order, t.grammar_id))
    return tuple(t.grammar_id for t in eligible)


def _build_baseline_review_pool(
    topics: tuple[GrammarTopic, ...],
    anchor: GrammarCEFRBand,
) -> tuple[str, ...]:
    """Topics below the placement anchor stay open for review, not primary learning."""
    baseline = [t for t in topics if cefr_rank(t.cefr_band) < cefr_rank(anchor)]
    baseline.sort(key=lambda t: (t.introduction_order, t.grammar_id))
    return tuple(t.grammar_id for t in baseline)


def _build_stretch_pool(
    topics: tuple[GrammarTopic, ...],
    *,
    anchor: GrammarCEFRBand,
    stretch_allowed: bool,
    candidate_ids: frozenset[str],
    by_id: dict[str, GrammarTopic],
) -> tuple[str, ...]:
    if not stretch_allowed:
        return ()
    nxt = _next_band(anchor)
    if nxt is None:
        return ()
    band_topics = sorted(
        (t for t in topics if t.cefr_band is nxt),
        key=lambda t: (t.introduction_order, t.grammar_id),
    )
    early: list[str] = []
    for t in band_topics:
        if all(p in candidate_ids for p in t.prerequisite_ids):
            early.append(t.grammar_id)
        if len(early) >= STRETCH_EARLY_TOPIC_LIMIT:
            break
    for gid in early:
        for p in by_id[gid].prerequisite_ids:
            if p not in by_id:
                raise GrammarProgressionError(f"Broken prerequisite chain: {gid} -> {p}")
    return tuple(early)


def _expand_unlocks(
    *,
    eligible_ids: tuple[str, ...],
    by_id: dict[str, GrammarTopic],
    seed_unlocked: frozenset[str],
    completed_ids: frozenset[str],
    candidate_ids: frozenset[str],
) -> frozenset[str]:
    """Monotonic unlock expansion. Never unlocks outside eligible set (except seed)."""
    unlocked: set[str] = set(seed_unlocked)
    changed = True
    while changed:
        changed = False
        for gid in eligible_ids:
            if gid in unlocked:
                continue
            topic = by_id[gid]
            prereqs = topic.prerequisite_ids
            if any(p not in by_id for p in prereqs):
                raise GrammarProgressionError(f"Broken prerequisite chain for {gid}")
            if any(p not in unlocked for p in prereqs):
                continue
            if not prereqs:
                if gid in candidate_ids:
                    unlocked.add(gid)
                    changed = True
                continue
            # Descendants require all parents completed (unlock gate — not mastery scores).
            if all(p in completed_ids for p in prereqs):
                unlocked.add(gid)
                changed = True
    return frozenset(unlocked)


def _peek_next_unlockable(
    *,
    eligible_ids: tuple[str, ...],
    by_id: dict[str, GrammarTopic],
    unlocked: frozenset[str],
    completed_ids: frozenset[str],
    candidate_ids: frozenset[str],
    learning_current: str | None,
    baseline_completed_ids: frozenset[str] = frozenset(),
) -> str | None:
    simulated_completed = set(completed_ids) | set(baseline_completed_ids)
    if learning_current:
        simulated_completed.add(learning_current)
    expanded = _expand_unlocks(
        eligible_ids=eligible_ids,
        by_id=by_id,
        seed_unlocked=unlocked,
        completed_ids=frozenset(simulated_completed),
        candidate_ids=candidate_ids,
    )
    newly = [
        gid
        for gid in eligible_ids
        if gid in expanded and gid not in unlocked and gid not in simulated_completed
    ]
    return newly[0] if newly else None


def _build_candidate_priorities(
    *,
    current: str | None,
    learning_queue: list[str],
    locked_ids: tuple[str, ...],
    stretch_ids: tuple[str, ...],
    order_index: dict[str, int],
) -> tuple[GrammarCandidatePriorityEntry, ...]:
    """Assign PRIMARY / SECONDARY / OPTIONAL / STRETCH without duplicating ids."""
    assigned: dict[str, GrammarCandidatePriority] = {}

    if current and current in learning_queue:
        assigned[current] = GrammarCandidatePriority.primary
    elif learning_queue:
        assigned[learning_queue[0]] = GrammarCandidatePriority.primary

    for gid in learning_queue:
        if gid not in assigned:
            assigned[gid] = GrammarCandidatePriority.secondary

    for gid in locked_ids:
        if gid not in assigned:
            assigned[gid] = GrammarCandidatePriority.optional

    for gid in stretch_ids:
        assigned[gid] = GrammarCandidatePriority.stretch  # stretch wins if also listed elsewhere

    entries = [
        GrammarCandidatePriorityEntry(grammar_id=gid, priority=pri)
        for gid, pri in assigned.items()
    ]
    entries.sort(
        key=lambda e: (_PRIORITY_RANK[e.priority], order_index.get(e.grammar_id, 10**9), e.grammar_id)
    )
    return tuple(entries)


def compute_progression_snapshot(
    *,
    catalog: GrammarCatalogSnapshot,
    anchor_cefr: GrammarCEFRBand,
    student: GrammarProgressionStudentState,
) -> GrammarProgressionSnapshot:
    """Deterministic progression decision. Identical inputs ⇒ identical snapshot."""
    topics = catalog.topics
    if not topics:
        raise GrammarProgressionError("Catalog has no topics")

    by_id = {t.grammar_id: t for t in topics}
    catalog_ids = frozenset(by_id)
    order_index = {t.grammar_id: t.introduction_order for t in topics}

    _validate_student_ids(student, catalog_ids)

    for t in topics:
        for p in t.prerequisite_ids:
            if p not in by_id:
                raise GrammarProgressionError(f"Broken prerequisite chain: {t.grammar_id} -> {p}")

    candidate_pool_ids = _build_candidate_pool(topics, anchor_cefr)
    candidate_set = frozenset(candidate_pool_ids)
    baseline_review_ids = _build_baseline_review_pool(topics, anchor_cefr)
    baseline_review_set = frozenset(baseline_review_ids)
    stretch_ids = _build_stretch_pool(
        topics,
        anchor=anchor_cefr,
        stretch_allowed=student.stretch_allowed,
        candidate_ids=candidate_set,
        by_id=by_id,
    )
    stretch_set = frozenset(stretch_ids)
    eligible_ids = tuple(dict.fromkeys([*candidate_pool_ids, *stretch_ids]))

    unlocked = _expand_unlocks(
        eligible_ids=eligible_ids,
        by_id=by_id,
        seed_unlocked=frozenset(student.unlocked_ids) | baseline_review_set,
        completed_ids=frozenset(student.completed_ids) | baseline_review_set,
        candidate_ids=candidate_set,
    )
    unlocked = frozenset(gid for gid in unlocked if gid in catalog_ids)

    unlocked_sorted = _sorted_unique(unlocked, order_index)
    locked_ids = _sorted_unique(candidate_set - unlocked, order_index)
    future_ids = _sorted_unique(catalog_ids - candidate_set - stretch_set, order_index)
    stretch_sorted = _sorted_unique(stretch_set, order_index)

    completed = frozenset(student.completed_ids)
    learning_queue = [
        gid
        for gid in unlocked_sorted
        if gid not in completed and cefr_rank(by_id[gid].cefr_band) >= cefr_rank(anchor_cefr)
    ]

    sticky = normalize_grammar_id(student.current_grammar_id) if student.current_grammar_id else None
    if sticky and sticky in learning_queue:
        current = sticky
    elif learning_queue:
        current = learning_queue[0]
    else:
        current = None

    if current and current in learning_queue:
        idx = learning_queue.index(current)
        if idx + 1 < len(learning_queue):
            next_id: str | None = learning_queue[idx + 1]
        else:
            next_id = _peek_next_unlockable(
                eligible_ids=eligible_ids,
                by_id=by_id,
                unlocked=unlocked,
                completed_ids=completed,
                candidate_ids=candidate_set,
                learning_current=current,
                baseline_completed_ids=baseline_review_set,
            )
    elif len(learning_queue) > 1:
        next_id = learning_queue[1]
    else:
        next_id = _peek_next_unlockable(
            eligible_ids=eligible_ids,
            by_id=by_id,
            unlocked=unlocked,
            completed_ids=completed,
            candidate_ids=candidate_set,
            learning_current=current,
            baseline_completed_ids=baseline_review_set,
        )

    priorities = _build_candidate_priorities(
        current=current,
        learning_queue=learning_queue,
        locked_ids=locked_ids,
        stretch_ids=stretch_sorted,
        order_index=order_index,
    )

    reasons = (
        f"anchor:{anchor_cefr.value}",
        f"stretch:{'on' if student.stretch_allowed else 'off'}",
        f"candidates:{len(candidate_pool_ids)}",
        f"unlocked:{len(unlocked_sorted)}",
        f"baseline_review:{len(baseline_review_ids)}",
        f"completed:{len(completed)}",
        f"current:{current or 'none'}",
        f"next:{next_id or 'none'}",
        f"priorities:{len(priorities)}",
    )

    return GrammarProgressionSnapshot(
        anchor_cefr=anchor_cefr,
        current_grammar_id=current,
        next_grammar_id=next_id,
        unlocked_ids=unlocked_sorted,
        locked_ids=locked_ids,
        future_ids=future_ids,
        stretch_ids=stretch_sorted,
        candidate_pool_ids=candidate_pool_ids,
        candidate_priorities=priorities,
        progression_reason=reasons,
        stretch_allowed=bool(student.stretch_allowed),
        enabled=True,
    )


def disabled_snapshot(*, anchor_cefr: GrammarCEFRBand) -> GrammarProgressionSnapshot:
    """Snapshot returned when LANG_GRAMMAR_ENGINE_ENABLED is false."""
    return GrammarProgressionSnapshot(
        anchor_cefr=anchor_cefr,
        current_grammar_id=None,
        next_grammar_id=None,
        unlocked_ids=(),
        locked_ids=(),
        future_ids=(),
        stretch_ids=(),
        candidate_pool_ids=(),
        candidate_priorities=(),
        progression_reason=("flag:LANG_GRAMMAR_ENGINE_ENABLED=false",),
        stretch_allowed=False,
        enabled=False,
    )
