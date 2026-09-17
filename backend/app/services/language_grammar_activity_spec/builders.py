"""Builders / fixtures helpers for ActivitySpecification (no Provider / Runtime)."""

from __future__ import annotations

from app.services.language_grammar_activity_spec.enums import (
    ACTIVITY_SCHEMA_VERSION,
    ACTIVITY_SPEC_PACKAGE_VERSION,
    GRAMMAR_SCHEMA_VERSION,
    ActivityDifficulty,
    ActivityType,
    EvaluationMode,
    EvidenceKind,
    ExpectedOutputType,
)
from app.services.language_grammar_activity_spec.serialization import with_fingerprint
from app.services.language_grammar_activity_spec.types import (
    ActivitySpecification,
    ActivityVersionSet,
    CompletionRule,
    EvidenceDeclaration,
    ExpectedOutputSpec,
    LocalizedText,
    ProviderMetadata,
)
from app.services.language_grammar_activity_spec.validation import validate_activity_specification


def loc(text: str, *, locale: str = "en") -> LocalizedText:
    return LocalizedText(values={locale: text}, default_locale=locale)


def build_minimal_specification(
    *,
    activity_id: str = "act_demo_1",
    activity_type: str = ActivityType.multiple_choice.value,
    grammar_topic: str = "gram_present_simple",
    lesson_id: str = "gless_1",
    step_id: str = "practice",
    locale: str = "en",
    validate: bool = True,
) -> ActivitySpecification:
    """Canonical minimal valid spec for tests / examples."""
    spec = ActivitySpecification(
        activity_id=activity_id,
        activity_type=activity_type,
        grammar_topic=grammar_topic,
        lesson_id=lesson_id,
        step_id=step_id,
        title=loc("Practice present simple", locale=locale),
        goal=loc("Produce correct present-simple forms", locale=locale),
        instructions=loc("Choose the correct option.", locale=locale),
        difficulty=ActivityDifficulty.guided,
        estimated_duration_seconds=120,
        grammar_targets=(grammar_topic,),
        expected_outputs=(
            ExpectedOutputSpec(
                output_id="out_choice",
                output_type=ExpectedOutputType.multiple_choice.value,
                required=True,
                options=("opt_a", "opt_b", "opt_c"),
            ),
        ),
        evaluation_mode=EvaluationMode.rule_based.value,
        completion_rules=(
            CompletionRule(rule_id="rule_all", kind="require_all_outputs"),
        ),
        hints=(loc("Think about the subject-verb agreement.", locale=locale),),
        evidence=(
            EvidenceDeclaration(
                evidence_id="ev_1",
                evidence_kind=EvidenceKind.formative.value,
                grammar_targets=(grammar_topic,),
                observation_types_hint=("formative",),
                required=True,
            ),
        ),
        provider_metadata=ProviderMetadata(
            provider_id="template",
            provider_version="1.0.0",
            generation_mode="template",
        ),
        localization_default_locale=locale,
        supported_locales=(locale,),
        versions=ActivityVersionSet(
            activity_schema_version=ACTIVITY_SCHEMA_VERSION,
            provider_version="1.0.0",
            planner_version="1.0.0",
            blueprint_version="1.0.0",
            catalog_version="1.0.0",
            grammar_schema_version=GRAMMAR_SCHEMA_VERSION,
            package_version=ACTIVITY_SPEC_PACKAGE_VERSION,
        ),
        payload={"correct_option": "opt_a"},
    )
    spec = with_fingerprint(spec)
    if validate:
        validate_activity_specification(spec)
    return spec
