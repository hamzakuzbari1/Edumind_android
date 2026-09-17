"""Build canonical ActivitySpecification from provider execution context (G3.35.1)."""

from __future__ import annotations

from app.services.language_grammar.enums import GrammarLessonStepKind
from app.services.language_grammar_activity_provider.types import (
    ActivityExecutionContext,
    GrammarActivityProviderId,
)
from app.services.language_grammar_activity_spec import (
    ACTIVITY_SCHEMA_VERSION,
    ACTIVITY_SPEC_PACKAGE_VERSION,
    GRAMMAR_SCHEMA_VERSION,
    ActivityDifficulty,
    ActivitySpecification,
    ActivityType,
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

# Deterministic step → activity type mapping (extensible; not UI).
_STEP_ACTIVITY_TYPE: dict[GrammarLessonStepKind, str] = {
    GrammarLessonStepKind.warmup: ActivityType.selection.value,
    GrammarLessonStepKind.quick_review: ActivityType.multiple_choice.value,
    GrammarLessonStepKind.explanation: ActivityType.selection.value,
    GrammarLessonStepKind.practice: ActivityType.multiple_choice.value,
    GrammarLessonStepKind.reinforcement: ActivityType.free_text.value,
    GrammarLessonStepKind.reading_reinforcement: ActivityType.free_text.value,
    GrammarLessonStepKind.listening_reinforcement: ActivityType.selection.value,
    GrammarLessonStepKind.writing_reinforcement: ActivityType.sentence_building.value,
    GrammarLessonStepKind.speaking_reinforcement: ActivityType.voice_recording.value,
    GrammarLessonStepKind.exit_check: ActivityType.fill_in_the_blank.value,
    GrammarLessonStepKind.summary: ActivityType.free_text.value,
    GrammarLessonStepKind.homework: ActivityType.free_text.value,
}

_STEP_OUTPUT_TYPE: dict[GrammarLessonStepKind, str] = {
    GrammarLessonStepKind.warmup: ExpectedOutputType.selection.value,
    GrammarLessonStepKind.quick_review: ExpectedOutputType.multiple_choice.value,
    GrammarLessonStepKind.explanation: ExpectedOutputType.selection.value,
    GrammarLessonStepKind.practice: ExpectedOutputType.multiple_choice.value,
    GrammarLessonStepKind.reinforcement: ExpectedOutputType.free_text.value,
    GrammarLessonStepKind.reading_reinforcement: ExpectedOutputType.free_text.value,
    GrammarLessonStepKind.listening_reinforcement: ExpectedOutputType.selection.value,
    GrammarLessonStepKind.writing_reinforcement: ExpectedOutputType.sentence_building.value,
    GrammarLessonStepKind.speaking_reinforcement: ExpectedOutputType.voice_recording.value,
    GrammarLessonStepKind.exit_check: ExpectedOutputType.fill_in_the_blank.value,
    GrammarLessonStepKind.summary: ExpectedOutputType.free_text.value,
    GrammarLessonStepKind.homework: ExpectedOutputType.free_text.value,
}


def _loc(text: str, *, locale: str) -> LocalizedText:
    return LocalizedText(values={locale: text}, default_locale=locale)


def build_activity_specification(
    context: ActivityExecutionContext,
    *,
    provider_id: GrammarActivityProviderId,
    title: str,
    goal: str,
    instructions: str,
    prompt_stub: str = "",
    generation_mode: str = "",
    cacheable: bool = False,
    validate: bool = True,
) -> ActivitySpecification:
    """Construct a valid ActivitySpecification — sole provider content contract."""
    step = context.step
    locale = context.student.locale or "en"
    grammar_id = context.blueprint.grammar_id
    activity_type = _STEP_ACTIVITY_TYPE.get(step.kind, ActivityType.free_text.value)
    output_type = _STEP_OUTPUT_TYPE.get(step.kind, ExpectedOutputType.free_text.value)
    activity_id = f"{provider_id.value}:{context.blueprint.fingerprint}:{step.step_id}"

    payload: dict[str, str] = {}
    if prompt_stub:
        payload["prompt_stub"] = prompt_stub
    if step.context_hint:
        payload["context_hint"] = step.context_hint
    if cacheable:
        payload["cacheable"] = "true"

    spec = ActivitySpecification(
        activity_id=activity_id,
        activity_type=activity_type,
        grammar_topic=grammar_id,
        lesson_id=context.runtime.lesson_id or context.blueprint.lesson_id,
        step_id=step.step_id,
        title=_loc(title or step.title or step.kind.value, locale=locale),
        goal=_loc(goal, locale=locale),
        instructions=_loc(instructions, locale=locale),
        difficulty=ActivityDifficulty.guided,
        estimated_duration_seconds=max(0, int(step.estimated_minutes) * 60),
        grammar_targets=(grammar_id,),
        expected_outputs=(
            ExpectedOutputSpec(
                output_id=f"out_{step.step_id}",
                output_type=output_type,
                required=True,
            ),
        ),
        evaluation_mode=EvaluationMode.rule_based.value,
        completion_rules=(
            CompletionRule(rule_id=f"rule_{step.step_id}", kind="require_all_outputs"),
        ),
        evidence=(
            EvidenceDeclaration(
                evidence_id=f"ev_{step.step_id}",
                evidence_kind=EvidenceKind.formative.value,
                grammar_targets=(grammar_id,),
                observation_types_hint=tuple(context.blueprint.evidence_plan.observation_types_hint)
                or ("formative",),
                required=bool(step.evidence_eligible),
            ),
        ),
        provider_metadata=ProviderMetadata(
            provider_id=provider_id.value,
            provider_version="1.1.0",
            generation_mode=generation_mode or provider_id.value,
            extras={"step_kind": step.kind.value},
        ),
        localization_default_locale=locale,
        supported_locales=(locale,),
        versions=ActivityVersionSet(
            activity_schema_version=ACTIVITY_SCHEMA_VERSION,
            provider_version="1.1.0",
            planner_version=str(context.blueprint.planner_version or ""),
            blueprint_version=str(context.blueprint.blueprint_version or ""),
            catalog_version=str(context.blueprint.catalog_version or ""),
            grammar_schema_version=int(context.blueprint.grammar_schema_version or GRAMMAR_SCHEMA_VERSION),
            package_version=ACTIVITY_SPEC_PACKAGE_VERSION,
        ),
        payload=payload,
    )
    spec = with_fingerprint(spec)
    if validate:
        validate_activity_specification(spec)
    return spec
