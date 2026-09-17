"""Topic Universe (W1) — canonical writing topic catalog and topic nodes."""

from __future__ import annotations

PACKAGE_VERSION = "1.0.0"
RESPONSIBILITY = "Canonical topic catalog, topic nodes, complexity curves per topic"

from app.services.language_writing_topic_universe.registry import (
    get_chain,
    get_topic,
    get_topic_catalog,
    get_universe_catalog,
    list_chains,
    list_chains_for_topic,
    list_topics,
)

__all__ = [
    "PACKAGE_VERSION",
    "RESPONSIBILITY",
    "get_universe_catalog",
    "get_topic_catalog",
    "get_topic",
    "get_chain",
    "list_topics",
    "list_chains",
    "list_chains_for_topic",
]
