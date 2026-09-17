"""Types and constants for canonical grammar lesson persistence."""

from __future__ import annotations

from enum import Enum


class GrammarCanonicalRevisionStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    VALIDATING = "validating"
    REVIEWABLE = "reviewable"
    PUBLISHED = "published"
    FAILED = "failed"
    ARCHIVED = "archived"


GRAMMAR_CANONICAL_REVISION_STATUSES = tuple(status.value for status in GrammarCanonicalRevisionStatus)
