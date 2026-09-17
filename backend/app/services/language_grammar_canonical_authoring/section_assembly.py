"""Deterministic assembly for accepted sectioned canonical grammar units."""

from __future__ import annotations

import json
from typing import Any

from app.models.language.grammar_canonical_lesson import (
    GrammarCanonicalLesson,
    GrammarCanonicalLessonRevisionUnitAttempt,
)
from app.services.language_grammar_activity_authoring.llm.lesson_schema import METHODOLOGY_SECTIONS
from app.services.language_grammar_canonical_authoring.types import RevisionValidationResult
from app.services.language_grammar_canonical_authoring.validation import (
    safe_diagnostics,
    validate_raw_authoring_output,
)
from app.services.language_grammar_canonical_authoring.section_validation import (
    required_form_covered,
    required_mistake_category_covered,
)
from app.services.language_grammar_pipeline.stages import _grammar_authoring_profile

REQUIRED_ACCEPTED_UNITS = ("blueprint", "concept", "examples", "rules", "practice", "production")


def assemble_canonical_lesson_from_units(
    *,
    lesson: GrammarCanonicalLesson,
    accepted_attempts: dict[str, GrammarCanonicalLessonRevisionUnitAttempt],
) -> RevisionValidationResult:
    missing = [unit for unit in REQUIRED_ACCEPTED_UNITS if unit not in accepted_attempts]
    if missing:
        return RevisionValidationResult(
            valid=False,
            diagnostics_json=safe_diagnostics("missing_accepted_units", "Missing units: " + ", ".join(missing)),
        )

    concept = accepted_attempts["concept"].public_payload_json or {}
    examples = accepted_attempts["examples"].public_payload_json or {}
    rules = accepted_attempts["rules"].public_payload_json or {}
    practice = accepted_attempts["practice"].public_payload_json or {}
    production = accepted_attempts["production"].public_payload_json or {}

    arabic = dict(concept.get("arabic_clarification") or {})
    if rules.get("arabic_english_contrast") and not arabic.get("arabic_english_contrast"):
        arabic["arabic_english_contrast"] = rules.get("arabic_english_contrast")

    student_content = {
        "orientation": concept.get("orientation") or {},
        "meaning_hook": concept.get("meaning_hook") or {},
        "model_examples": examples.get("model_examples") or [],
        "noticing": examples.get("noticing") or {},
        "concept_explanation": concept.get("concept_explanation") or {},
        "form_and_rules": {
            "patterns": rules.get("patterns") or [],
            "rule_notes": rules.get("rule_notes") or [],
            "use_cases": examples.get("use_cases") or [],
            "visual_summary": rules.get("visual_summary") or [],
        },
        "arabic_clarification": {
            "arabic": arabic.get("arabic"),
            "arabic_speaker_warning": arabic.get("arabic_speaker_warning"),
            "arabic_english_contrast": arabic.get("arabic_english_contrast"),
        },
        "contrasts_and_mistakes": rules.get("contrasts_and_mistakes") or [],
        "understanding_checks": practice.get("understanding_checks") or [],
        "guided_practice": practice.get("guided_practice") or [],
        "supported_production": production.get("supported_production") or [],
        "transfer": production.get("transfer") or {},
        "exit_check": production.get("exit_check") or {},
        "reflection": production.get("reflection") or {},
    }
    metadata = {
        "noticing": (accepted_attempts["examples"].private_metadata_json or {}).get("noticing") or [],
        "understanding_checks": (accepted_attempts["practice"].private_metadata_json or {}).get("understanding_checks") or [],
        "guided_practice": (accepted_attempts["practice"].private_metadata_json or {}).get("guided_practice") or [],
        "supported_production": (accepted_attempts["production"].private_metadata_json or {}).get("supported_production") or [],
        "transfer": (accepted_attempts["production"].private_metadata_json or {}).get("transfer") or [],
        "exit_check": (accepted_attempts["production"].private_metadata_json or {}).get("exit_check") or [],
    }
    cross = _cross_section_check(student_content, accepted_attempts["blueprint"].blueprint_json or {}, lesson=lesson)
    if cross is not None:
        return RevisionValidationResult(valid=False, diagnostics_json=cross)
    return validate_raw_authoring_output(
        {
            "student_content": student_content,
            "server_teaching_metadata": metadata,
        },
        lesson=lesson,
    )


def _cross_section_check(
    student: dict[str, Any],
    blueprint: dict[str, Any],
    *,
    lesson: GrammarCanonicalLesson,
) -> dict[str, Any] | None:
    if tuple(student.keys()) != METHODOLOGY_SECTIONS:
        return safe_diagnostics("assembly_section_mismatch", "Assembled student_content does not match canonical section order")
    expected_forms = _profile_required_form_keys(lesson)
    actual_forms = _as_list(blueprint.get("required_forms"))
    if expected_forms and set(actual_forms) != set(expected_forms):
        missing = sorted(set(expected_forms) - set(actual_forms))
        extra = sorted(set(actual_forms) - set(expected_forms))
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("extra: " + ", ".join(extra))
        return safe_diagnostics(
            "blueprint_required_forms_mismatch",
            "Blueprint required_forms must match current server profile; " + "; ".join(details),
        )
    ids = _collect_public_ids(student)
    duplicates = sorted({item_id for item_id in ids if ids.count(item_id) > 1})
    if duplicates:
        return safe_diagnostics("duplicate_global_ids", "Duplicate public IDs: " + ", ".join(duplicates))
    blob = json.dumps(student, ensure_ascii=False, sort_keys=True).lower()
    for form in blueprint.get("required_forms") or []:
        if not required_form_covered(str(form), blob, lesson=lesson):
            return safe_diagnostics("required_form_missing_after_assembly", f"Required form missing: {form}")
    if lesson.grammar_id == "gram_be_present":
        for category in blueprint.get("mistake_intentions") or []:
            if not required_mistake_category_covered(str(category), blob, lesson=lesson):
                return safe_diagnostics(
                    "required_mistake_category_missing_after_assembly",
                    f"Required mistake category missing: {category}",
                )
    if not student["supported_production"] or not student["transfer"]:
        return safe_diagnostics("missing_independent_use", "Production and transfer sections are required")
    return None


def _profile_required_form_keys(lesson: GrammarCanonicalLesson) -> list[str]:
    if lesson.grammar_id != "gram_be_present":
        return []
    profile = _grammar_authoring_profile((lesson.grammar_id,))
    values = profile.get("required_form_keys") or []
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _collect_public_ids(value: Any) -> list[str]:
    ids: list[str] = []
    if isinstance(value, dict):
        if isinstance(value.get("id"), str) and value["id"].strip():
            ids.append(value["id"].strip())
        for child in value.values():
            ids.extend(_collect_public_ids(child))
    elif isinstance(value, list):
        for item in value:
            ids.extend(_collect_public_ids(item))
    return ids
