"""DEPRECATED legacy ActivityResult adapter (G3.35.1).

ActivitySpecification is the ONLY canonical activity content contract.
These helpers exist temporarily for migration — do not use in new code.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

from app.services.language_grammar.enums import GrammarLessonStepKind, GrammarReinforcementSkill
from app.services.language_grammar_activity_provider.types import GrammarActivityProviderId
from app.services.language_grammar_activity_spec import (
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
    with_fingerprint,
)

_WARN = (
    "ActivityResult is deprecated (G3.35.1). Use ActivitySpecification as the sole "
    "activity content contract. This adapter will be removed in a future release."
)


@dataclass(frozen=True, slots=True)
class ActivityResult:
    """DEPRECATED — legacy provider payload. Prefer ActivitySpecification.

    .. deprecated:: G3.35.1
       ActivitySpecification is the only source of truth.
       Use ``legacy_activity_result_from_specification`` /
       ``specification_from_legacy_activity_result`` only for temporary migration.
    """

    activity_id: str
    provider_id: GrammarActivityProviderId
    step_id: str
    step_kind: GrammarLessonStepKind
    title: str = ""
    body: str = ""
    prompt_stub: str = ""
    materials: tuple[str, ...] = ()
    skill: GrammarReinforcementSkill | None = None
    cacheable: bool = False
    metadata: dict[str, str] | None = None
    schema_version: int = 1


def legacy_activity_result_from_specification(spec: ActivitySpecification) -> ActivityResult:
    """DEPRECATED: project ActivitySpecification → legacy ActivityResult."""
    warnings.warn(_WARN, DeprecationWarning, stacklevel=2)
    try:
        provider_id = GrammarActivityProviderId(spec.provider_metadata.provider_id)
    except ValueError:
        provider_id = GrammarActivityProviderId.template
    try:
        step_kind = GrammarLessonStepKind(
            spec.provider_metadata.extras.get("step_kind") or GrammarLessonStepKind.practice.value
        )
    except ValueError:
        step_kind = GrammarLessonStepKind.practice
    skill = None
    return ActivityResult(
        activity_id=spec.activity_id,
        provider_id=provider_id,
        step_id=spec.step_id,
        step_kind=step_kind,
        title=spec.title.resolve(),
        body=spec.instructions.resolve(),
        prompt_stub=spec.payload.get("prompt_stub", ""),
        materials=(),
        skill=skill,
        cacheable=spec.payload.get("cacheable") == "true",
        metadata={
            "grammar_id": spec.grammar_topic,
            "lesson_id": spec.lesson_id,
        },
        schema_version=1,
    )


def specification_from_legacy_activity_result(
    legacy: ActivityResult,
    *,
    grammar_topic: str = "",
    lesson_id: str = "",
    locale: str = "en",
) -> ActivitySpecification:
    """DEPRECATED: lift legacy ActivityResult → ActivitySpecification."""
    warnings.warn(_WARN, DeprecationWarning, stacklevel=2)
    gid = grammar_topic or (legacy.metadata or {}).get("grammar_id") or "gram_unknown"
    lid = lesson_id or (legacy.metadata or {}).get("lesson_id") or "lesson_unknown"

    def _loc(text: str) -> LocalizedText:
        return LocalizedText(values={locale: text}, default_locale=locale)

    spec = ActivitySpecification(
        activity_id=legacy.activity_id,
        activity_type=ActivityType.free_text.value,
        grammar_topic=gid,
        lesson_id=lid,
        step_id=legacy.step_id,
        title=_loc(legacy.title or legacy.step_id),
        goal=_loc(legacy.title or legacy.step_id),
        instructions=_loc(legacy.body or legacy.title or legacy.step_id),
        grammar_targets=(gid,),
        expected_outputs=(
            ExpectedOutputSpec(
                output_id=f"out_{legacy.step_id}",
                output_type=ExpectedOutputType.free_text.value,
                required=True,
            ),
        ),
        evaluation_mode=EvaluationMode.rule_based.value,
        completion_rules=(CompletionRule(rule_id=f"rule_{legacy.step_id}", kind="require_all_outputs"),),
        evidence=(
            EvidenceDeclaration(
                evidence_id=f"ev_{legacy.step_id}",
                evidence_kind=EvidenceKind.formative.value,
                grammar_targets=(gid,),
                observation_types_hint=("formative",),
                required=True,
            ),
        ),
        provider_metadata=ProviderMetadata(
            provider_id=legacy.provider_id.value,
            provider_version="legacy",
            generation_mode="legacy_adapter",
            extras={"step_kind": legacy.step_kind.value},
        ),
        localization_default_locale=locale,
        supported_locales=(locale,),
        versions=ActivityVersionSet(provider_version="legacy"),
        payload={
            "prompt_stub": legacy.prompt_stub,
            "cacheable": "true" if legacy.cacheable else "false",
            "legacy": "1",
        },
    )
    return with_fingerprint(spec)
