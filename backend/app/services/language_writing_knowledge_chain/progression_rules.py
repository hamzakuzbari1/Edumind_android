"""Knowledge chain progression rules (W1)."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing.enums import OfficialWritingCEFR, WritingTopicId
from app.services.language_writing_knowledge_chain.types import WritingKnowledgeChain, WritingKnowledgeChainNode


@dataclass(frozen=True, slots=True)
class ProgressionDecision:
    allowed: bool
    reason: str
    next_node_id: str | None = None


_CEFR_ORDER = tuple(OfficialWritingCEFR)


def _cefr_rank(level: OfficialWritingCEFR) -> int:
    return _CEFR_ORDER.index(level)


def entry_node(chain: WritingKnowledgeChain) -> WritingKnowledgeChainNode | None:
    return chain.entry_node


def next_linear_node(chain: WritingKnowledgeChain, current_node_id: str) -> WritingKnowledgeChainNode | None:
    node = chain.node_by_id(current_node_id)
    if node is None or not node.next_node_ids:
        return None
    return chain.node_by_id(node.next_node_ids[0])


def can_access_node(
    *,
    chain: WritingKnowledgeChain,
    node_id: str,
    completed_node_ids: frozenset[str],
    official_cefr: OfficialWritingCEFR,
) -> ProgressionDecision:
    """Determine if a student may start a chain node."""
    node = chain.node_by_id(node_id)
    if node is None:
        return ProgressionDecision(False, "Node not found in chain")

    # Official CEFR floor: lesson CEFR may be at or below official + 1 band for stretch
    if _cefr_rank(node.official_cefr) > _cefr_rank(official_cefr) + 1:
        return ProgressionDecision(False, "Official CEFR too low for this node")

    # Prerequisites (previous nodes in chain)
    for prev in node.previous_node_ids:
        if prev not in completed_node_ids:
            prev_node = chain.node_by_id(prev)
            label = prev_node.label if prev_node else prev
            return ProgressionDecision(False, f"Complete '{label}' first")

    # Entry node always allowed if CEFR ok
    if not node.previous_node_ids:
        return ProgressionDecision(True, "Chain entry node", node_id)

    return ProgressionDecision(True, "Prerequisites satisfied", node_id)


def recommend_next_node(
    *,
    chain: WritingKnowledgeChain,
    completed_node_ids: frozenset[str],
    official_cefr: OfficialWritingCEFR,
) -> ProgressionDecision:
    """Recommend the next node in a chain for continuous journey."""
    if not completed_node_ids:
        entry = entry_node(chain)
        if entry is None:
            return ProgressionDecision(False, "Empty chain")
        return can_access_node(
            chain=chain,
            node_id=entry.node_id,
            completed_node_ids=completed_node_ids,
            official_cefr=official_cefr,
        )

    # Find last completed by highest position
    completed = [chain.node_by_id(nid) for nid in completed_node_ids]
    completed = [n for n in completed if n is not None]
    if not completed:
        return ProgressionDecision(False, "No valid completed nodes")
    last = max(completed, key=lambda n: n.position)

    if last.next_node_ids:
        nxt_id = last.next_node_ids[0]
        return can_access_node(
            chain=chain,
            node_id=nxt_id,
            completed_node_ids=completed_node_ids,
            official_cefr=official_cefr,
        )

    return ProgressionDecision(False, "Chain complete", None)


def chains_for_topic_in_order(topic_id: WritingTopicId, chains: tuple[WritingKnowledgeChain, ...]) -> tuple[WritingKnowledgeChain, ...]:
    """Stable ordering for topic chain presentation."""
    return tuple(sorted((c for c in chains if c.topic_id == topic_id), key=lambda c: c.chain_id))
