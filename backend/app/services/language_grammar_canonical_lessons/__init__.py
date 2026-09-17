"""Canonical grammar lesson persistence foundation."""

from app.services.language_grammar_canonical_lessons.errors import GrammarCanonicalLessonError
from app.services.language_grammar_canonical_lessons.hashing import compute_canonical_lesson_content_hash
from app.services.language_grammar_canonical_lessons.repository import (
    archive_revision,
    assert_transition_allowed,
    create_next_draft_revision,
    get_active_published_revision_by_identity,
    get_active_published_revision_by_lesson_id,
    get_canonical_lesson_by_id,
    get_canonical_lesson_by_identity,
    get_or_create_canonical_lesson,
    list_revisions_for_canonical_lesson,
    mark_revision_failed,
    mark_revision_generating,
    mark_revision_reviewable,
    mark_revision_status,
    mark_revision_validating,
    publish_reviewable_revision,
    read_revision_by_id,
    store_or_update_draft_content,
)
from app.services.language_grammar_canonical_lessons.types import (
    GRAMMAR_CANONICAL_REVISION_STATUSES,
    GrammarCanonicalRevisionStatus,
)

PACKAGE = "language_grammar_canonical_lessons"
RESPONSIBILITY = (
    "Canonical grammar lesson identity and revision persistence; publishing, "
    "immutability, and private metadata boundaries only."
)

__all__ = [
    "PACKAGE",
    "RESPONSIBILITY",
    "GRAMMAR_CANONICAL_REVISION_STATUSES",
    "GrammarCanonicalLessonError",
    "GrammarCanonicalRevisionStatus",
    "archive_revision",
    "assert_transition_allowed",
    "compute_canonical_lesson_content_hash",
    "create_next_draft_revision",
    "get_active_published_revision_by_identity",
    "get_active_published_revision_by_lesson_id",
    "get_canonical_lesson_by_id",
    "get_canonical_lesson_by_identity",
    "get_or_create_canonical_lesson",
    "list_revisions_for_canonical_lesson",
    "mark_revision_failed",
    "mark_revision_generating",
    "mark_revision_reviewable",
    "mark_revision_status",
    "mark_revision_validating",
    "publish_reviewable_revision",
    "read_revision_by_id",
    "store_or_update_draft_content",
]
