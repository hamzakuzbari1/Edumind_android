"""Grammar Catalog (G1) — sole owner of GrammarTopic definitions + DAG.

RESPONSIBILITY: Topic definitions, metadata, CEFR introduction bands,
prerequisite/future DAG, and read-only catalog queries.
No progression, mastery, review, planner, runtime, Claude, or analytics logic.
"""

from __future__ import annotations

from app.services.language_grammar_catalog.catalog import (
    CATALOG_LANGUAGE_CODE,
    all_grammar_ids,
    get_default_catalog,
    get_english_catalog,
    get_topic,
    list_topics,
    reload_english_catalog,
    require_topic,
    topics_for_cefr,
    topics_up_to_cefr,
    validate_default_catalog,
)
from app.services.language_grammar_catalog.loader import (
    clear_curriculum_cache,
    curriculum_root,
    language_curriculum_dir,
    load_grammar_curriculum,
)
from app.services.language_grammar_catalog.types import (
    GRAMMAR_CATALOG_SCHEMA_VERSION,
    GRAMMAR_CATALOG_VERSION,
    GrammarCatalogSnapshot,
    GrammarEvidenceRequirements,
    GrammarTopic,
)
from app.services.language_grammar_catalog.validation import (
    CatalogValidationIssue,
    CatalogValidationResult,
    validate_catalog,
    validate_curriculum_progression,
)

PACKAGE_VERSION = "1.0.0"
RESPONSIBILITY = (
    "Sole owner of GrammarTopic definitions (curriculum/{language}/grammar YAML), "
    "prereq DAG, CEFR intro bands, display_code, best_reinforcement_skills, "
    "recommended_contexts, minimum_context_diversity"
)

__all__ = [
    "CATALOG_LANGUAGE_CODE",
    "CatalogValidationIssue",
    "CatalogValidationResult",
    "GRAMMAR_CATALOG_SCHEMA_VERSION",
    "GRAMMAR_CATALOG_VERSION",
    "GrammarCatalogSnapshot",
    "GrammarEvidenceRequirements",
    "GrammarTopic",
    "PACKAGE_VERSION",
    "RESPONSIBILITY",
    "all_grammar_ids",
    "clear_curriculum_cache",
    "curriculum_root",
    "get_default_catalog",
    "get_english_catalog",
    "get_topic",
    "language_curriculum_dir",
    "list_topics",
    "load_grammar_curriculum",
    "reload_english_catalog",
    "require_topic",
    "topics_for_cefr",
    "topics_up_to_cefr",
    "validate_catalog",
    "validate_curriculum_progression",
    "validate_default_catalog",
]
