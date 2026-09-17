"""Topic Universe registry (W1) — load and query the canonical catalog."""

from __future__ import annotations

from functools import lru_cache

from app.services.language_writing.enums import WritingTopicId
from app.services.language_writing_knowledge_chain.types import WritingKnowledgeChain
from app.services.language_writing_topic_universe.types import WritingUniverseCatalog
from app.services.language_writing_topic_universe.catalog_v1 import build_topic_catalog, build_universe_catalog
from app.services.language_writing_topic_universe.types import WritingTopicCatalog, WritingTopicNode


@lru_cache(maxsize=1)
def get_universe_catalog() -> WritingUniverseCatalog:
    """Return the canonical v1 Writing Universe (topics + chains)."""
    return build_universe_catalog()


@lru_cache(maxsize=1)
def get_topic_catalog() -> WritingTopicCatalog:
    return build_topic_catalog()


def get_topic(topic_id: WritingTopicId) -> WritingTopicNode | None:
    for topic in get_topic_catalog().topics:
        if topic.topic_id == topic_id:
            return topic
    return None


def get_chain(chain_id: str) -> WritingKnowledgeChain | None:
    return get_universe_catalog().chain_by_id(chain_id)


def list_topics() -> tuple[WritingTopicNode, ...]:
    return get_topic_catalog().topics


def list_chains() -> tuple[WritingKnowledgeChain, ...]:
    return get_universe_catalog().chains


def list_chains_for_topic(topic_id: WritingTopicId) -> tuple[WritingKnowledgeChain, ...]:
    return get_universe_catalog().chains_for_topic(topic_id)
