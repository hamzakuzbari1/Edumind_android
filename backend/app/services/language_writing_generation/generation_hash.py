"""Generation hash (W5) — deterministic fingerprint of canonical lesson payload."""

from __future__ import annotations

import hashlib
import json

from app.services.language_writing_generation.canonical_lesson_types import WritingCanonicalGeneratedLesson

GENERATION_HASH_VERSION = "5.0.0"

GENERATION_HASH_CANONICAL_FIELDS: frozenset[str] = frozenset(
    {
        "mission_title",
        "writing_context",
        "instructions",
        "writing_prompt",
        "constraints",
        "checklist",
        "tips",
        "learning_outcomes",
        "success_criteria",
        "expected_output",
        "grammar_display",
        "vocabulary_display",
        "blueprint_hash",
    }
)


def compute_generation_hash(lesson: WritingCanonicalGeneratedLesson) -> str:
    """SHA-256 of canonical lesson presentation payload + blueprint_hash."""
    payload = {
        "mission_title": lesson.mission_title,
        "writing_context": lesson.writing_context,
        "instructions": list(lesson.instructions),
        "writing_prompt": lesson.writing_prompt,
        "constraints": list(lesson.constraints),
        "checklist": list(lesson.checklist),
        "tips": list(lesson.tips),
        "learning_outcomes": list(lesson.learning_outcomes),
        "success_criteria": list(lesson.success_criteria),
        "expected_output": lesson.expected_output,
        "grammar_display": lesson.grammar_display,
        "vocabulary_display": lesson.vocabulary_display,
        "blueprint_hash": lesson.blueprint_hash,
        "hash_version": GENERATION_HASH_VERSION,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
