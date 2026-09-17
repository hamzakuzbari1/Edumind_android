"""Student-safe inspection for canonical grammar lesson revisions."""

from __future__ import annotations

from typing import Any

from app.models.language.grammar_canonical_lesson import (
    GrammarCanonicalLesson,
    GrammarCanonicalLessonRevision,
)
from app.services.language_grammar_catalog.catalog import get_topic
from app.services.language_grammar_canonical_authoring.validation import validation_summary


def build_student_safe_inspection(
    *,
    lesson: GrammarCanonicalLesson,
    revision: GrammarCanonicalLessonRevision,
    include_private_diagnostics: bool = False,
) -> dict[str, Any]:
    student = dict(revision.student_content_json or {})
    out: dict[str, Any] = {
        "canonical_identity": {
            "lesson_id": str(lesson.id),
            "grammar_id": lesson.grammar_id,
            "display_name": _display_name_for_lesson(lesson),
            "cefr_level": lesson.cefr_level,
            "locale": lesson.locale,
            "methodology_version": lesson.methodology_version,
        },
        "revision": {
            "revision_id": str(revision.id),
            "revision_number": revision.revision_number,
            "status": revision.status,
            "schema_version": revision.schema_version,
            "prompt_version": revision.prompt_version,
            "catalog_version": revision.catalog_version,
            "content_hash": revision.content_hash,
            "authoring_provider": revision.authoring_provider,
            "authoring_model": revision.authoring_model,
            "generated_at": _iso(revision.generated_at),
            "reviewed_at": _iso(revision.reviewed_at),
            "published_at": _iso(revision.published_at),
            "archived_at": _iso(revision.archived_at),
        },
        "learner_sections": {
            "understand": {
                "orientation": student.get("orientation"),
                "meaning_hook": student.get("meaning_hook"),
                "concept_explanation": student.get("concept_explanation"),
                "arabic_clarification": student.get("arabic_clarification"),
            },
            "see_how_it_works": {
                "model_examples": student.get("model_examples"),
                "noticing": student.get("noticing"),
            },
            "rules_and_mistakes": {
                "form_and_rules": student.get("form_and_rules"),
                "contrasts_and_mistakes": student.get("contrasts_and_mistakes"),
            },
            "guided_practice": {
                "understanding_checks": student.get("understanding_checks"),
                "guided_practice": student.get("guided_practice"),
                "exit_check": student.get("exit_check"),
            },
            "use_it_yourself": {
                "supported_production": student.get("supported_production"),
                "transfer": student.get("transfer"),
                "reflection": student.get("reflection"),
            },
        },
        "validation_summary": validation_summary(revision.diagnostics_json),
    }
    if include_private_diagnostics:
        out["private_diagnostics"] = validation_summary(revision.diagnostics_json)
    return out


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


def _display_name_for_lesson(lesson: GrammarCanonicalLesson) -> str:
    topic = get_topic(lesson.grammar_id)
    if topic is not None and topic.display_name:
        return topic.display_name
    return lesson.grammar_id.replace("gram_", "").replace("_", " ").title()
