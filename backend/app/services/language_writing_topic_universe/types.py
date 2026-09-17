"""Types for the Writing Topic Universe (W0)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_writing.enums import ContextComplexity, OfficialWritingCEFR, WritingTopicId
from app.services.language_writing_knowledge_chain.types import WritingKnowledgeChain


@dataclass(frozen=True, slots=True)
class WritingTopicNode:
    """Canonical topic entry in the Topic Universe."""

    topic_id: WritingTopicId
    label: str
    description: str
    chain_ids: tuple[str, ...]
    default_complexity_range: tuple[int, int]  # min/max ContextComplexity for topic
    vocabulary_domains: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TopicComplexityBand:
    """Expected complexity progression for a topic at a given Official CEFR."""

    official_cefr: OfficialWritingCEFR
    topic_id: WritingTopicId
    min_complexity: ContextComplexity
    max_complexity: ContextComplexity
    typical_complexity: ContextComplexity


@dataclass(frozen=True, slots=True)
class WritingTopicCatalog:
    """Versioned Topic Universe snapshot."""

    catalog_version: str
    topics: tuple[WritingTopicNode, ...]
    complexity_bands: tuple[TopicComplexityBand, ...] = ()

    def topic_ids(self) -> frozenset[WritingTopicId]:
        return frozenset(t.topic_id for t in self.topics)


@dataclass(frozen=True, slots=True)
class TopicSelectionContext:
    """Inputs for topic-aware lesson selection (contracts only — W0)."""

    topic_id: WritingTopicId
    context_complexity: ContextComplexity
    chain_id: str
    chain_node_id: str


@dataclass(frozen=True, slots=True)
class WritingUniverseCatalog:
    """Complete W1 educational world — topics + chains."""

    catalog_version: str
    topics: tuple[WritingTopicNode, ...]
    chains: tuple[WritingKnowledgeChain, ...]

    def chains_for_topic(self, topic_id: WritingTopicId) -> tuple[WritingKnowledgeChain, ...]:
        return tuple(c for c in self.chains if c.topic_id == topic_id)

    def chain_by_id(self, chain_id: str) -> WritingKnowledgeChain | None:
        for chain in self.chains:
            if chain.chain_id == chain_id:
                return chain
        return None

    def node_by_id(self, chain_id: str, node_id: str):
        chain = self.chain_by_id(chain_id)
        return chain.node_by_id(node_id) if chain else None
