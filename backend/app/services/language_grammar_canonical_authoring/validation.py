"""Validation helpers for persisted canonical grammar lesson revisions."""

from __future__ import annotations

import json
from typing import Any

from app.models.language.grammar_canonical_lesson import (
    GrammarCanonicalLesson,
    GrammarCanonicalLessonRevision,
)
from app.services.language_grammar_activity_authoring.llm.errors import (
    LLMInvalidJSONError,
    LLMSchemaError,
)
from app.services.language_grammar_activity_authoring.llm.lesson_validation import (
    validate_canonical_lesson_output,
)
from app.services.language_grammar_activity_authoring.llm.parser import extract_json_object
from app.services.language_grammar_canonical_authoring.types import RevisionValidationResult
from app.services.language_grammar_canonical_lessons.hashing import compute_canonical_lesson_content_hash
from app.services.language_grammar_pipeline.stages import _grammar_authoring_profile


def safe_diagnostics(code: str, message: str, *, field_path: str = "", value_description: str = "") -> dict[str, Any]:
    return {
        "code": code,
        "message": str(message)[:500],
        "field_path": field_path,
        "value_description": value_description[:220],
    }


def support_targets_for_grammar(grammar_id: str) -> tuple[str, ...]:
    profile = _grammar_authoring_profile((grammar_id,))
    support = profile.get("support_grammar_targets") or []
    if not isinstance(support, list):
        return ()
    return tuple(str(item).strip() for item in support if str(item).strip())


def max_contrasts_and_mistakes_for_grammar(grammar_id: str) -> int | None:
    if grammar_id != "gram_be_present":
        return None
    profile = _grammar_authoring_profile((grammar_id,))
    categories = profile.get("mistake_categories") or []
    if not isinstance(categories, list):
        return None
    count = len([str(item).strip() for item in categories if str(item).strip()])
    return count if count > 4 else None


def validate_raw_authoring_output(
    raw_output: str | dict[str, Any],
    *,
    lesson: GrammarCanonicalLesson,
) -> RevisionValidationResult:
    try:
        data = extract_json_object(raw_output) if isinstance(raw_output, str) else dict(raw_output)
        _reject_raw_grammar_ids(data.get("student_content") or {}, grammar_id=lesson.grammar_id)
        canonical = validate_canonical_lesson_output(
            data,
            allowed_targets=(lesson.grammar_id,),
            support_targets=support_targets_for_grammar(lesson.grammar_id),
            cefr_level=lesson.cefr_level,
            raw_output=raw_output if isinstance(raw_output, str) else "",
            max_contrasts_and_mistakes=max_contrasts_and_mistakes_for_grammar(lesson.grammar_id),
        )
        content_hash = compute_canonical_lesson_content_hash(
            student_content_json=canonical.student_content,
            server_teaching_metadata_json=canonical.server_teaching_metadata,
            schema_version="grammar_lesson_authoring_v2",
            methodology_version=lesson.methodology_version,
        )
        return RevisionValidationResult(
            valid=True,
            normalized_student_content=canonical.student_content,
            normalized_server_teaching_metadata=canonical.server_teaching_metadata,
            content_hash=content_hash,
            diagnostics_json={"status": "valid"},
        )
    except (LLMInvalidJSONError, LLMSchemaError, ValueError) as exc:
        return RevisionValidationResult(
            valid=False,
            diagnostics_json=_diagnostics_from_exception(exc),
        )


def validate_persisted_revision_payload(
    *,
    lesson: GrammarCanonicalLesson,
    revision: GrammarCanonicalLessonRevision,
    require_existing_hash: bool = True,
) -> RevisionValidationResult:
    if not revision.student_content_json:
        return RevisionValidationResult(
            valid=False,
            diagnostics_json=safe_diagnostics("missing_student_content", "Revision has no student content"),
        )
    if not revision.server_teaching_metadata_json:
        return RevisionValidationResult(
            valid=False,
            diagnostics_json=safe_diagnostics(
                "missing_server_teaching_metadata",
                "Revision has no server teaching metadata",
            ),
        )
    if revision.schema_version != "grammar_lesson_authoring_v2":
        return RevisionValidationResult(
            valid=False,
            diagnostics_json=safe_diagnostics(
                "schema_version_mismatch",
                f"Expected grammar_lesson_authoring_v2; got {revision.schema_version!r}",
            ),
        )

    raw = {
        "student_content": revision.student_content_json,
        "server_teaching_metadata": revision.server_teaching_metadata_json,
    }
    result = validate_raw_authoring_output(raw, lesson=lesson)
    if not result.valid:
        return result
    if require_existing_hash and result.content_hash != revision.content_hash:
        return RevisionValidationResult(
            valid=False,
            diagnostics_json=safe_diagnostics(
                "content_hash_mismatch",
                "Persisted content hash does not match canonical payload",
            ),
            normalized_student_content=result.normalized_student_content,
            normalized_server_teaching_metadata=result.normalized_server_teaching_metadata,
            content_hash=result.content_hash,
        )
    return result


def validation_summary(diagnostics_json: dict[str, Any] | None) -> dict[str, Any]:
    diagnostics = dict(diagnostics_json or {})
    return {
        "status": diagnostics.get("status") or ("failed" if diagnostics.get("code") else "unknown"),
        "code": diagnostics.get("code") or "",
        "message": diagnostics.get("message") or "",
        "field_path": diagnostics.get("field_path") or "",
    }


def _diagnostics_from_exception(exc: Exception) -> dict[str, Any]:
    code = str(getattr(exc, "code", "") or "")
    if not code:
        code = getattr(exc, "args", ["validation_failed"])[0] if getattr(exc, "args", None) else "validation_failed"
    if not isinstance(code, str) or ":" in code or " " in code:
        code = exc.__class__.__name__
    return safe_diagnostics(code, str(exc))


def _reject_raw_grammar_ids(student_content: dict[str, Any], *, grammar_id: str) -> None:
    blob = json.dumps(student_content, ensure_ascii=False, sort_keys=True)
    if grammar_id and grammar_id in blob:
        raise LLMSchemaError("raw_grammar_id_exposed", "Student-facing content contains raw grammar_id")
