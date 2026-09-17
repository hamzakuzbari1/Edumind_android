"""Placeholder Authoring Strategy base (V1.3) — no LLM / prompts."""

from __future__ import annotations

from app.services.language_grammar_activity_authoring.types import AuthoringRequest
from app.services.language_grammar_activity_spec import (
    ACTIVITY_SCHEMA_VERSION,
    ACTIVITY_SPEC_PACKAGE_VERSION,
    GRAMMAR_SCHEMA_VERSION,
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

# activity_type → expected output type (defaults to same code when present).
_OUTPUT_TYPE_FALLBACK = {
    "selection": ExpectedOutputType.selection.value,
    "multiple_choice": ExpectedOutputType.multiple_choice.value,
    "free_text": ExpectedOutputType.free_text.value,
    "voice_recording": ExpectedOutputType.voice_recording.value,
    "ordering": ExpectedOutputType.ordering.value,
    "matching": ExpectedOutputType.matching.value,
    "fill_in_the_blank": ExpectedOutputType.fill_in_the_blank.value,
    "conversation": ExpectedOutputType.conversation.value,
    "sentence_building": ExpectedOutputType.sentence_building.value,
}


def _loc(text: str, *, locale: str) -> LocalizedText:
    return LocalizedText(values={locale: text}, default_locale=locale)


class PlaceholderAuthoringStrategy:
    """Deterministic placeholder author — produces ActivitySpecification only."""

    strategy_version: str = "1.0.0"

    def __init__(self, strategy_id: str, supported_activity_types: frozenset[str]) -> None:
        self._strategy_id = strategy_id
        self._supported_activity_types = frozenset(supported_activity_types)

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    @property
    def supported_activity_types(self) -> frozenset[str]:
        return self._supported_activity_types

    def supports(self, activity_type: str) -> bool:
        return activity_type in self._supported_activity_types

    def author(self, request: AuthoringRequest) -> ActivitySpecification:
        ctx = request.context
        locale = ctx.localization or ctx.student_profile.locale or "en"
        primary = ctx.grammar_targets[0]
        activity_type = ctx.activity_type
        output_type = _OUTPUT_TYPE_FALLBACK.get(activity_type, ExpectedOutputType.free_text.value)
        step_id = ctx.lesson_context.step_id or "practice"
        lesson_id = ctx.lesson_context.lesson_id or "lesson_authored"
        activity_id = (
            f"auth:{self.strategy_id}:{primary}:{activity_type}:{step_id}:"
            f"{ctx.versions.catalog_version}:{ctx.versions.blueprint_version}"
        )
        title = f"{self.strategy_id.replace('_', ' ').title()}: {primary}"
        goal = ctx.learning_objective.strip()
        instructions = (
            f"Placeholder {self.strategy_id} activity for {primary}. "
            f"Objective: {goal}."
        )
        if ctx.lesson_context.context_hint:
            instructions = f"{instructions} Context: {ctx.lesson_context.context_hint}."

        options: tuple[str, ...] = ()
        if activity_type in {"multiple_choice", "selection"}:
            options = ("opt_a", "opt_b", "opt_c")

        payload: dict[str, str] = {
            "strategy_id": self.strategy_id,
            "generation_mode": "authoring_placeholder",
            "student_cefr": ctx.student_cefr,
            "teacher_persona": ctx.teacher_persona.persona_id,
        }
        if options:
            payload["correct_option"] = options[0]

        versions = ctx.versions
        spec = ActivitySpecification(
            activity_id=activity_id,
            activity_type=activity_type,
            grammar_topic=primary,
            lesson_id=lesson_id,
            step_id=step_id,
            title=_loc(title, locale=locale),
            goal=_loc(goal, locale=locale),
            instructions=_loc(instructions, locale=locale),
            difficulty=ctx.difficulty,
            estimated_duration_seconds=120,
            grammar_targets=tuple(ctx.grammar_targets),
            expected_outputs=(
                ExpectedOutputSpec(
                    output_id=f"out_{step_id}",
                    output_type=output_type,
                    required=True,
                    options=options,
                ),
            ),
            evaluation_mode=EvaluationMode.rule_based.value,
            completion_rules=(
                CompletionRule(rule_id=f"rule_{step_id}", kind="require_all_outputs"),
            ),
            evidence=(
                EvidenceDeclaration(
                    evidence_id=f"ev_{step_id}",
                    evidence_kind=EvidenceKind.formative.value,
                    grammar_targets=tuple(ctx.grammar_targets),
                    observation_types_hint=("formative",),
                    required=True,
                ),
            ),
            provider_metadata=ProviderMetadata(
                provider_id="authoring",
                provider_version=versions.provider_version or self.strategy_version,
                generation_mode="authoring_placeholder",
                extras={
                    "strategy_id": self.strategy_id,
                    "authoring_version": versions.authoring_version,
                },
            ),
            localization_default_locale=locale,
            supported_locales=(locale,),
            versions=ActivityVersionSet(
                activity_schema_version=versions.activity_schema_version or ACTIVITY_SCHEMA_VERSION,
                provider_version=versions.provider_version,
                planner_version=versions.planner_version,
                blueprint_version=versions.blueprint_version,
                catalog_version=versions.catalog_version,
                grammar_schema_version=versions.grammar_schema_version or GRAMMAR_SCHEMA_VERSION,
                package_version=ACTIVITY_SPEC_PACKAGE_VERSION,
            ),
            payload=payload,
        )
        spec = with_fingerprint(spec)
        validate_activity_specification(spec)
        return spec
