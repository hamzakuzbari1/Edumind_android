"""Grammar Catalog integrity validation (G1) — catalog package only."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_grammar.id_canon import is_canonical_grammar_id
from app.services.language_grammar_catalog.cefr_order import CEFR_SEQUENCE, cefr_rank
from app.services.language_grammar_catalog.types import GrammarCatalogSnapshot, GrammarTopic

REQUIRED_METADATA_ATTRS: tuple[str, ...] = (
    "grammar_id",
    "display_name",
    "cefr_band",
    "introduction_order",
    "prerequisite_ids",
    "future_topic_ids",
    "learning_objectives",
    "demonstration_patterns",
    "example_sentences",
    "common_errors",
    "best_reinforcement_skills",
    "recommended_contexts",
    "minimum_context_diversity",
    "evidence_requirements",
    "mastery_threshold",
    "review_priority",
)


@dataclass
class CatalogValidationIssue:
    code: str
    message: str
    grammar_id: str = ""


@dataclass
class CatalogValidationResult:
    valid: bool = True
    issues: list[CatalogValidationIssue] = field(default_factory=list)

    def add(self, code: str, message: str, *, grammar_id: str = "") -> None:
        self.issues.append(CatalogValidationIssue(code=code, message=message, grammar_id=grammar_id))
        self.valid = False


def _detect_prereq_cycles(topics: tuple[GrammarTopic, ...]) -> list[str]:
    ids = {t.grammar_id for t in topics}
    by_id = {t.grammar_id: t for t in topics}
    state: dict[str, int] = dict.fromkeys(ids, 0)  # 0=unvisited, 1=visiting, 2=done
    cycle_nodes: list[str] = []

    def dfs(grammar_id: str, path: list[str]) -> bool:
        state[grammar_id] = 1
        path.append(grammar_id)
        node = by_id[grammar_id]
        for prereq in node.prerequisite_ids:
            if prereq not in ids:
                continue
            if state[prereq] == 1:
                cycle_nodes.extend(path[path.index(prereq) :] + [prereq])
                return True
            if state[prereq] == 0 and dfs(prereq, path):
                return True
        path.pop()
        state[grammar_id] = 2
        return False

    for gid in ids:
        if state[gid] == 0:
            dfs(gid, [])
    return cycle_nodes


def validate_catalog(snapshot: GrammarCatalogSnapshot) -> CatalogValidationResult:
    """Full catalog integrity validation."""
    result = CatalogValidationResult()
    topics = snapshot.topics
    if not topics:
        result.add("empty_catalog", "Catalog has no topics")
        return result

    ids = [t.grammar_id for t in topics]
    if len(ids) != len(set(ids)):
        seen: set[str] = set()
        for gid in ids:
            if gid in seen:
                result.add("duplicate_id", f"Duplicate grammar_id: {gid}", grammar_id=gid)
            seen.add(gid)

    orders = [t.introduction_order for t in topics]
    if len(orders) != len(set(orders)):
        result.add("duplicate_introduction_order", "introduction_order values must be unique")

    id_set = set(ids)
    by_id = {t.grammar_id: t for t in topics}

    for topic in topics:
        gid = topic.grammar_id
        if not is_canonical_grammar_id(gid):
            result.add("invalid_id", f"Non-canonical grammar_id: {gid}", grammar_id=gid)
        if not (topic.display_name or "").strip():
            result.add("missing_display_name", "display_name is required", grammar_id=gid)
        for attr in REQUIRED_METADATA_ATTRS:
            if not hasattr(topic, attr):
                result.add("missing_metadata_field", f"Missing field {attr}", grammar_id=gid)

        if not topic.learning_objectives:
            result.add("missing_objectives", "learning_objectives must be non-empty", grammar_id=gid)
        if not topic.demonstration_patterns:
            result.add("missing_patterns", "demonstration_patterns must be non-empty", grammar_id=gid)
        if not topic.example_sentences:
            result.add("missing_examples", "example_sentences must be non-empty", grammar_id=gid)
        if not topic.common_errors:
            result.add("missing_errors", "common_errors must be non-empty", grammar_id=gid)
        if not topic.best_reinforcement_skills:
            result.add("missing_reinforcement", "best_reinforcement_skills must be non-empty", grammar_id=gid)
        if len(topic.best_reinforcement_skills) > 3:
            result.add(
                "too_many_reinforcement_skills",
                "best_reinforcement_skills should recommend at most 3 skills",
                grammar_id=gid,
            )
        if not topic.recommended_contexts:
            result.add("missing_contexts", "recommended_contexts must be non-empty", grammar_id=gid)
        if topic.minimum_context_diversity < 1:
            result.add("bad_context_diversity", "minimum_context_diversity must be >= 1", grammar_id=gid)
        if not (0.0 < topic.mastery_threshold <= 100.0):
            result.add("bad_mastery_threshold", "mastery_threshold must be in (0, 100]", grammar_id=gid)
        if topic.review_priority < 1 or topic.review_priority > 5:
            result.add("bad_review_priority", "review_priority must be 1–5", grammar_id=gid)
        if topic.review_half_life_days <= 0:
            result.add("bad_half_life", "review_half_life_days must be > 0", grammar_id=gid)

        # No duplicated parents
        if len(topic.prerequisite_ids) != len(set(topic.prerequisite_ids)):
            result.add("duplicate_prerequisites", "Duplicate prerequisite_ids", grammar_id=gid)
        if len(topic.future_topic_ids) != len(set(topic.future_topic_ids)):
            result.add("duplicate_futures", "Duplicate future_topic_ids", grammar_id=gid)

        for prereq in topic.prerequisite_ids:
            if prereq not in id_set:
                result.add("broken_prerequisite", f"Missing prerequisite: {prereq}", grammar_id=gid)
                continue
            parent = by_id[prereq]
            if cefr_rank(parent.cefr_band) > cefr_rank(topic.cefr_band):
                result.add(
                    "prereq_cefr_inversion",
                    f"Prerequisite {prereq} introduced at higher CEFR than {gid}",
                    grammar_id=gid,
                )
            if parent.introduction_order >= topic.introduction_order:
                result.add(
                    "prereq_order_inversion",
                    f"Prerequisite {prereq} must have lower introduction_order than {gid}",
                    grammar_id=gid,
                )

        for future in topic.future_topic_ids:
            if future not in id_set:
                result.add("broken_future", f"Missing future topic: {future}", grammar_id=gid)
                continue
            child = by_id[future]
            if gid not in child.prerequisite_ids:
                result.add(
                    "future_edge_inconsistent",
                    f"future_topic_ids lists {future} but reverse prerequisite missing",
                    grammar_id=gid,
                )

        # Self-edges forbidden
        if gid in topic.prerequisite_ids:
            result.add("self_prerequisite", "Topic cannot prerequisite itself", grammar_id=gid)
        if gid in topic.future_topic_ids:
            result.add("self_future", "Topic cannot list itself as future", grammar_id=gid)

    cycles = _detect_prereq_cycles(topics)
    if cycles:
        result.add("circular_dependency", f"Prerequisite cycle involving: {' -> '.join(cycles)}")

    # Orphans: topics with no path from roots (no prereqs) via future edges — allowed
    # if they are roots. Flag topics that are unreachable from any root AND have prereqs
    # that don't exist (already covered). Also flag isolated non-roots with missing parents.
    roots = [t for t in topics if not t.prerequisite_ids]
    if not roots:
        result.add("no_roots", "Catalog must have at least one root topic (no prerequisites)")

    # Every CEFR band that has topics should have a sensible intro progression
    for band in CEFR_SEQUENCE:
        band_topics = [t for t in topics if t.cefr_band is band]
        if not band_topics:
            # C2 may exist; empty band is a curriculum warning handled elsewhere
            continue
        orders = [t.introduction_order for t in band_topics]
        if orders != sorted(orders):
            result.add(
                "band_order_unsorted",
                f"{band.value} topics are not sorted by introduction_order in snapshot",
            )

    return result


def validate_curriculum_progression(snapshot: GrammarCatalogSnapshot) -> CatalogValidationResult:
    """Curriculum integrity: each CEFR band progresses without illogical jumps."""
    result = CatalogValidationResult()
    topics = snapshot.topics
    by_id = {t.grammar_id: t for t in topics}

    for band in CEFR_SEQUENCE:
        band_topics = sorted(
            (t for t in topics if t.cefr_band is band),
            key=lambda t: t.introduction_order,
        )
        if not band_topics:
            if band is CEFR_SEQUENCE[0]:
                result.add("missing_a1", "A1 band must contain topics")
            continue

        # Within-band: prerequisites may reuse earlier bands (allowed).
        # Disallow only forward CEFR dependencies (already covered in integrity).
        for topic in band_topics:
            for prereq in topic.prerequisite_ids:
                parent = by_id.get(prereq)
                if parent is None:
                    continue
                if cefr_rank(parent.cefr_band) > cefr_rank(topic.cefr_band):
                    result.add(
                        "illogical_cefr_jump",
                        f"{topic.grammar_id} depends on higher-band prerequisite {prereq}",
                        grammar_id=topic.grammar_id,
                    )

        # Continuity: each band after A1 should link to earlier-band material
        if band is not CEFR_SEQUENCE[0] and band_topics:
            prev_rank = cefr_rank(band) - 1
            connected = False
            for topic in band_topics:
                for prereq in topic.prerequisite_ids:
                    parent = by_id.get(prereq)
                    if parent and cefr_rank(parent.cefr_band) <= prev_rank:
                        connected = True
                        break
                if connected:
                    break
            if not connected:
                result.add(
                    "band_disconnected",
                    f"{band.value} has no prerequisite link to earlier CEFR bands",
                )

    # Global unlock order must be strictly increasing along every prerequisite edge
    for topic in topics:
        for prereq in topic.prerequisite_ids:
            parent = by_id.get(prereq)
            if parent and parent.introduction_order >= topic.introduction_order:
                result.add(
                    "unlock_order_violation",
                    f"Unlock order broken: {prereq} -> {topic.grammar_id}",
                    grammar_id=topic.grammar_id,
                )

    return result
