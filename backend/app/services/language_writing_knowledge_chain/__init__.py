"""Knowledge Chain (W1) — chain registry, validation, progression rules."""

from __future__ import annotations

PACKAGE_VERSION = "1.0.0"
RESPONSIBILITY = "Knowledge chain registry, chain nodes, prerequisites, chain progression"

from app.services.language_writing_knowledge_chain.progression_rules import (
    can_access_node,
    recommend_next_node,
)
from app.services.language_writing_knowledge_chain.validator import validate_chain, validate_universe

__all__ = [
    "PACKAGE_VERSION",
    "RESPONSIBILITY",
    "validate_chain",
    "validate_universe",
    "can_access_node",
    "recommend_next_node",
]
