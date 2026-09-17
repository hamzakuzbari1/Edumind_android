"""Knowledge dependency chains for curriculum progression (Phase 2.3)."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_listening_quality.types import ListeningSituationKind

TRAVEL_AIRPORT_CHAIN: tuple[str, ...] = (
    "airport_orientation",
    "check_in",
    "security",
    "boarding",
    "announcement",
    "delay",
    "immigration",
)

CHAIN_SITUATION_MAP: dict[str, tuple[ListeningSituationKind, ...]] = {
    "airport_orientation": (ListeningSituationKind.airport, ListeningSituationKind.public_announcement),
    "check_in": (ListeningSituationKind.airport, ListeningSituationKind.hotel),
    "security": (ListeningSituationKind.airport, ListeningSituationKind.public_announcement),
    "boarding": (ListeningSituationKind.airport, ListeningSituationKind.travel),
    "announcement": (
        ListeningSituationKind.public_announcement,
        ListeningSituationKind.airport,
        ListeningSituationKind.news,
    ),
    "delay": (ListeningSituationKind.airport, ListeningSituationKind.customer_support, ListeningSituationKind.travel),
    "immigration": (ListeningSituationKind.airport, ListeningSituationKind.travel),
}

SITUATION_TO_NODE: dict[ListeningSituationKind, str] = {}
for node, situations in CHAIN_SITUATION_MAP.items():
    for situation in situations:
        SITUATION_TO_NODE.setdefault(situation, node)


@dataclass(frozen=True, slots=True)
class KnowledgeChain:
    chain_id: str
    nodes: tuple[str, ...]


KNOWLEDGE_CHAINS: tuple[KnowledgeChain, ...] = (
    KnowledgeChain("travel_airport", TRAVEL_AIRPORT_CHAIN),
)


def knowledge_node_for_situation(situation: ListeningSituationKind) -> str:
    return SITUATION_TO_NODE.get(situation, situation.value)


def next_chain_node(chain: KnowledgeChain, completed_nodes: set[str]) -> str | None:
    for node in chain.nodes:
        if node not in completed_nodes:
            return node
    return None


def progression_boost(
    situation: ListeningSituationKind,
    *,
    seen_nodes: set[str],
    chain: KnowledgeChain = KNOWLEDGE_CHAINS[0],
) -> float:
    target = next_chain_node(chain, seen_nodes)
    if not target:
        return 0.5
    node = knowledge_node_for_situation(situation)
    if node == target:
        return 1.8
    allowed = CHAIN_SITUATION_MAP.get(target, ())
    if situation in allowed:
        return 1.4
    if node in seen_nodes:
        return 0.6
    return 1.0
