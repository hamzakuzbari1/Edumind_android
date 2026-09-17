"""Structured output parser for canonical Claude grammar lesson authoring."""

from __future__ import annotations

import json
import re
from typing import Any

from app.services.language_grammar_activity_authoring.llm.errors import (
    LLMInvalidJSONError,
    LLMSchemaError,
)
from app.services.language_grammar_activity_authoring.llm.lesson_schema import (
    CANONICAL_LESSON_SCHEMA_VERSION,
    LESSON_PACKAGE_VERSION,
    METHODOLOGY_VERSION,
    canonical_lesson_to_payload,
)
from app.services.language_grammar_activity_authoring.llm.lesson_validation import (
    validate_canonical_lesson_output,
)
from app.services.language_grammar_activity_authoring.types import AuthoringRequest
from app.services.language_grammar_activity_spec import (
    ACTIVITY_SPEC_PACKAGE_VERSION,
    ActivityDifficulty,
    ActivitySpecification,
    ActivityVersionSet,
    CompletionRule,
    EvaluationMode,
    EvidenceDeclaration,
    EvidenceKind,
    ExpectedOutputSpec,
    ExpectedOutputType,
    LocalizedText,
    ProviderMetadata,
    validate_activity_specification,
    with_fingerprint,
)
from app.services.language_grammar_activity_spec.registry import get_default_spec_registry


def extract_json_object(raw: str) -> dict[str, Any]:
    """Parse structured JSON only; tolerate fenced JSON but reject documents."""
    text = (raw or "").strip()
    if not text:
        raise LLMInvalidJSONError("empty_json", "LLM returned empty response")
    if text.startswith("#") or text.startswith("<html") or text.startswith("<!DOCTYPE"):
        raise LLMInvalidJSONError("non_json_document", "LLM returned non-JSON document")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        candidate = fence.group(1) if fence else None
        if candidate is None:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                candidate = text[start : end + 1]
        if not candidate:
            raise LLMInvalidJSONError("invalid_json", "LLM response is not valid JSON") from None
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise LLMInvalidJSONError("invalid_json", f"LLM JSON parse failed: {exc}") from exc

    if not isinstance(parsed, dict):
        raise LLMInvalidJSONError("invalid_json_root", "LLM JSON root must be an object")
    return parsed


def _loc(text: str, *, locale: str) -> LocalizedText:
    return LocalizedText(values={locale: text}, default_locale=locale)


def _output_type_for(activity_type: str) -> str:
    return {
        "selection": ExpectedOutputType.selection.value,
        "multiple_choice": ExpectedOutputType.multiple_choice.value,
        "free_text": ExpectedOutputType.free_text.value,
        "voice_recording": ExpectedOutputType.voice_recording.value,
        "ordering": ExpectedOutputType.ordering.value,
        "matching": ExpectedOutputType.matching.value,
        "fill_in_the_blank": ExpectedOutputType.fill_in_the_blank.value,
        "conversation": ExpectedOutputType.conversation.value,
        "sentence_building": ExpectedOutputType.sentence_building.value,
    }.get(activity_type, ExpectedOutputType.free_text.value)


def _display_name_from_request(request: AuthoringRequest) -> str:
    raw = request.context.extras.get("grammar_profile_json")
    if raw:
        try:
            profile = json.loads(raw)
        except json.JSONDecodeError:
            profile = {}
        if isinstance(profile, dict):
            name = str(profile.get("display_name") or "").strip()
            if name:
                return name
    return request.context.grammar_targets[0].replace("gram_", "").replace("_", " ").title()


def _support_targets_from_request(request: AuthoringRequest) -> tuple[str, ...]:
    raw = request.context.extras.get("grammar_profile_json")
    if not raw:
        return ()
    try:
        profile = json.loads(raw)
    except json.JSONDecodeError:
        return ()
    if not isinstance(profile, dict):
        return ()
    support = profile.get("support_grammar_targets") or []
    if not isinstance(support, list):
        return ()
    return tuple(str(item).strip() for item in support if str(item).strip())


def _max_contrasts_and_mistakes_from_request(request: AuthoringRequest) -> int | None:
    targets = tuple(request.context.grammar_targets)
    if not targets or targets[0] != "gram_be_present":
        return None
    raw = request.context.extras.get("grammar_profile_json")
    if not raw:
        return None
    try:
        profile = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(profile, dict):
        return None
    categories = profile.get("mistake_categories") or []
    if not isinstance(categories, list):
        return None
    count = len([str(item).strip() for item in categories if str(item).strip()])
    return count if count > 4 else None


def _title_goal_from_lesson(data: dict[str, Any], *, display_name: str) -> tuple[str, str, str]:
    student = data.get("student_content") or {}
    orientation = student.get("orientation") if isinstance(student.get("orientation"), dict) else {}
    meaning_hook = student.get("meaning_hook") if isinstance(student.get("meaning_hook"), dict) else {}
    title = f"Grammar Lesson: {display_name}"
    goal = str(meaning_hook.get("why_it_matters") or meaning_hook.get("situation") or "").strip()
    if not goal:
        goal = f"Understand and practice {display_name}."
    instructions = str(orientation.get("teacher_script") or orientation.get("text") or "").strip()
    if not instructions:
        instructions = "Complete the lesson steps in order."
    return title, goal, instructions


def parse_activity_specification_json(
    raw: str,
    request: AuthoringRequest,
    *,
    provider_id: str,
) -> ActivitySpecification:
    """Parse Claude content and attach the server-owned ActivitySpecification envelope."""
    data = extract_json_object(raw)
    ctx = request.context
    activity_type = ctx.activity_type
    if not get_default_spec_registry().is_activity_type_known(activity_type):
        raise LLMSchemaError("unknown_activity_type", f"Unknown activity type: {activity_type}")

    req_targets = tuple(ctx.grammar_targets)
    if not req_targets:
        raise LLMSchemaError("missing_grammar_targets", "Grammar Targets required")

    canonical = validate_canonical_lesson_output(
        data,
        allowed_targets=req_targets,
        support_targets=_support_targets_from_request(request),
        cefr_level=ctx.student_cefr,
        raw_output=raw,
        max_contrasts_and_mistakes=_max_contrasts_and_mistakes_from_request(request),
    )

    locale = ctx.localization or ctx.student_profile.locale or "en"
    primary = req_targets[0]
    lesson_id = ctx.lesson_context.lesson_id or "lesson_authored"
    step_id = ctx.lesson_context.step_id or "practice"
    display_name = _display_name_from_request(request)
    title, goal, instructions = _title_goal_from_lesson(data, display_name=display_name)
    versions = ctx.versions
    activity_id = (
        f"llm:{provider_id}:{primary}:{activity_type}:{step_id}:"
        f"{versions.catalog_version}:{versions.blueprint_version}"
    )
    options = ("opt_a", "opt_b", "opt_c") if activity_type in {"multiple_choice", "selection"} else ()
    payload = canonical_lesson_to_payload(canonical, grammar_focus=primary)
    payload["generation_mode"] = "llm_canonical_grammar_lesson_authoring"
    payload["canonical_lesson_schema_version"] = CANONICAL_LESSON_SCHEMA_VERSION
    payload["methodology_version"] = METHODOLOGY_VERSION
    payload["lesson_id"] = lesson_id
    payload["grammar_id"] = primary
    payload["display_name"] = display_name
    payload["cefr_level"] = ctx.student_cefr

    spec = ActivitySpecification(
        activity_id=activity_id,
        activity_type=activity_type,
        grammar_topic=primary,
        lesson_id=lesson_id,
        step_id=step_id,
        title=_loc(title, locale=locale),
        goal=_loc(ctx.learning_objective or goal, locale=locale),
        instructions=_loc(instructions, locale=locale),
        difficulty=ctx.difficulty if isinstance(ctx.difficulty, ActivityDifficulty) else ActivityDifficulty.guided,
        estimated_duration_seconds=900,
        grammar_targets=req_targets,
        expected_outputs=(
            ExpectedOutputSpec(
                output_id=f"out_{step_id}",
                output_type=_output_type_for(activity_type),
                required=True,
                options=options,
            ),
        ),
        evaluation_mode=EvaluationMode.rule_based.value,
        completion_rules=(CompletionRule(rule_id=f"rule_{step_id}", kind="require_all_outputs"),),
        evidence=(
            EvidenceDeclaration(
                evidence_id=f"ev_{step_id}",
                evidence_kind=EvidenceKind.formative.value,
                grammar_targets=req_targets,
                observation_types_hint=("formative",),
                required=True,
            ),
        ),
        provider_metadata=ProviderMetadata(
            provider_id=provider_id,
            provider_version=versions.provider_version or LESSON_PACKAGE_VERSION,
            generation_mode="llm_canonical_grammar_lesson_authoring",
            extras={
                "lesson_schema_version": CANONICAL_LESSON_SCHEMA_VERSION,
                "methodology_version": METHODOLOGY_VERSION,
                "lesson_package_version": LESSON_PACKAGE_VERSION,
            },
        ),
        localization_default_locale=locale,
        supported_locales=(locale,),
        versions=ActivityVersionSet(
            activity_schema_version=versions.activity_schema_version,
            provider_version=versions.provider_version or LESSON_PACKAGE_VERSION,
            planner_version=versions.planner_version,
            blueprint_version=versions.blueprint_version,
            catalog_version=versions.catalog_version,
            grammar_schema_version=versions.grammar_schema_version,
            package_version=ACTIVITY_SPEC_PACKAGE_VERSION,
        ),
        payload=payload,
    )

    try:
        validate_activity_specification(spec)
    except Exception as exc:  # noqa: BLE001
        raise LLMSchemaError("schema_validation_failed", str(exc)) from exc
    return with_fingerprint(spec)
