"""Lesson Validator (W5) — validate normalized draft against blueprint metadata."""

from __future__ import annotations

from app.services.language_writing_generation.normalizer_types import WritingNormalizedLessonDraft
from app.services.language_writing_generation.validator_types import (
    VALIDATOR_VERSION,
    ValidationIssue,
    ValidationIssueCode,
    ValidationResult,
    ValidationSeverity,
)
from app.services.language_writing_lesson_planner.types import WritingLessonBlueprint


def _grammar_token(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _contains_grammar_reference(text: str, grammar_id: str) -> bool:
    token = _grammar_token(grammar_id)
    haystack = _grammar_token(text)
    return token in haystack or token.replace("_", " ") in haystack


def _vocabulary_overlap(items: tuple[str, ...], required: tuple[str, ...]) -> bool:
    if not required:
        return True
    normalized_items = {v.strip().lower() for v in items}
    normalized_required = {v.strip().lower() for v in required}
    return bool(normalized_items & normalized_required)


def validate_lesson_draft(
    draft: WritingNormalizedLessonDraft,
    blueprint: WritingLessonBlueprint,
) -> ValidationResult:
    """Validate draft fields against blueprint — consistency checks only."""
    issues: list[ValidationIssue] = []

    if not draft.mission_title.strip():
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.missing_required_field,
                field="mission_title",
                message="mission_title is required",
            )
        )
    if not draft.writing_context.strip():
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.missing_required_field,
                field="writing_context",
                message="writing_context is required",
            )
        )
    if not draft.instructions:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.missing_required_field,
                field="instructions",
                message="instructions must be non-empty",
            )
        )
    if not draft.writing_prompt.strip():
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.missing_required_field,
                field="writing_prompt",
                message="writing_prompt is required",
            )
        )

    primary_grammar = blueprint.grammar_targets.primary
    grammar_refs = " ".join([draft.grammar_display, *draft.instructions, *draft.constraints])
    if not _contains_grammar_reference(grammar_refs, primary_grammar):
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.grammar_metadata_mismatch,
                field="grammar_display",
                message=f"Primary grammar '{primary_grammar}' not referenced in draft",
            )
        )

    vocab_refs = tuple(draft.vocabulary_display.split(",")) + draft.instructions + draft.constraints
    if not _vocabulary_overlap(vocab_refs, blueprint.vocabulary_targets.primary):
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.vocabulary_metadata_mismatch,
                field="vocabulary_display",
                message="Primary vocabulary lemmas not referenced in draft",
            )
        )

    if draft.success_criteria and draft.success_criteria != blueprint.success_criteria_labels:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.success_criteria_mismatch,
                field="success_criteria",
                message="success_criteria differ from blueprint labels",
                severity=ValidationSeverity.warning,
            )
        )
    elif not draft.success_criteria:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.success_criteria_mismatch,
                field="success_criteria",
                message="success_criteria missing — repair may restore from blueprint",
                severity=ValidationSeverity.warning,
            )
        )

    expected = blueprint.expected_writing_output.value
    if draft.expected_output and draft.expected_output != expected:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.expected_output_mismatch,
                field="expected_output",
                message=f"expected_output '{draft.expected_output}' != blueprint '{expected}'",
            )
        )
    elif not draft.expected_output:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.expected_output_mismatch,
                field="expected_output",
                message="expected_output missing — repair may restore from blueprint",
                severity=ValidationSeverity.warning,
            )
        )

    word_limit_ref = str(blueprint.success_criteria.min_words)
    constraints_text = " ".join(draft.constraints).lower()
    if word_limit_ref not in constraints_text and not draft.constraints:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.word_limit_missing,
                field="constraints",
                message="Word limits not present in constraints",
                severity=ValidationSeverity.warning,
            )
        )

    cefr_ref = blueprint.official_cefr.value.lower()
    if cefr_ref not in constraints_text and cefr_ref not in draft.writing_context.lower():
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.cefr_metadata_missing,
                field="constraints",
                message=f"CEFR band '{blueprint.official_cefr.value}' not referenced",
                severity=ValidationSeverity.warning,
            )
        )

    if draft.learning_outcomes and set(draft.learning_outcomes) != set(blueprint.learning_outcomes):
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.learning_outcomes_mismatch,
                field="learning_outcomes",
                message="learning_outcomes differ from blueprint",
                severity=ValidationSeverity.warning,
            )
        )
    elif not draft.learning_outcomes:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.learning_outcomes_mismatch,
                field="learning_outcomes",
                message="learning_outcomes missing — repair may restore from blueprint",
                severity=ValidationSeverity.warning,
            )
        )

    required_schema_fields = ("mission_title", "writing_context", "instructions", "writing_prompt")
    for field in required_schema_fields:
        if not getattr(draft, field):
            issues.append(
                ValidationIssue(
                    code=ValidationIssueCode.output_schema_incomplete,
                    field=field,
                    message=f"Output schema incomplete: {field}",
                )
            )

    errors = [i for i in issues if i.severity == ValidationSeverity.error]
    return ValidationResult(
        passed=len(errors) == 0,
        issues=tuple(issues),
        validator_version=VALIDATOR_VERSION,
    )
