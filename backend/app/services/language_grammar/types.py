"""Core Grammar spine constants and shared contracts (G0)."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_grammar.ownership import (
    GRAMMAR_JSONB_NAMESPACE,
    VOCABULARY_JSONB_NAMESPACE_RESERVED,
)

GRAMMAR_CORE_TYPES_VERSION = "0.1.0"

# Storage keys inside promotion_readiness_json["grammar"]
GRAMMAR_STORAGE_MASTERY_KEY = "mastery"
GRAMMAR_STORAGE_REVIEW_KEY = "review"
GRAMMAR_STORAGE_PROGRESSION_KEY = "progression"
GRAMMAR_STORAGE_RUNTIME_KEY = "runtime"
GRAMMAR_STORAGE_SCHEMA_VERSION_KEY = "schema_version"
GRAMMAR_STORAGE_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class GrammarStorageNamespaces:
    """Documented JSONB layout for the Grammar spine (writers enforced in G1+)."""

    root: str = GRAMMAR_JSONB_NAMESPACE
    mastery: str = GRAMMAR_STORAGE_MASTERY_KEY
    review: str = GRAMMAR_STORAGE_REVIEW_KEY
    progression: str = GRAMMAR_STORAGE_PROGRESSION_KEY
    runtime: str = GRAMMAR_STORAGE_RUNTIME_KEY
    schema_version_key: str = GRAMMAR_STORAGE_SCHEMA_VERSION_KEY
    schema_version: int = GRAMMAR_STORAGE_SCHEMA_VERSION
    # Future Vocabulary spine — reserved to prevent key collisions.
    vocabulary_reserved: str = VOCABULARY_JSONB_NAMESPACE_RESERVED
