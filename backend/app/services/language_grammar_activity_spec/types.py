"""Canonical Activity Specification models (G3.35).

Providers return ActivitySpecification only — never UI, Runtime state, or free markdown.
Skill Executors / Renderers consume this contract without knowing Provider internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_grammar_activity_spec.enums import (
    ACTIVITY_SCHEMA_VERSION,
    ACTIVITY_SPEC_PACKAGE_VERSION,
    GRAMMAR_SCHEMA_VERSION,
    ActivityDifficulty,
    EvaluationMode,
)


@dataclass(frozen=True, slots=True)
class LocalizedText:
    """Language-independent text: locale code → string. Architecture is not English-hardcoded."""

    values: dict[str, str] = field(default_factory=dict)
    default_locale: str = "en"

    def resolve(self, locale: str | None = None) -> str:
        loc = locale or self.default_locale
        if loc in self.values:
            return self.values[loc]
        if self.default_locale in self.values:
            return self.values[self.default_locale]
        if self.values:
            return next(iter(self.values.values()))
        return ""

    def __bool__(self) -> bool:
        return any(str(v).strip() for v in self.values.values())


@dataclass(frozen=True, slots=True)
class ActivityAssetRef:
    """Opaque asset reference — never a rendered UI component."""

    asset_id: str
    kind: str = "media"
    uri: str = ""
    locale: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ActivityReference:
    """Pedagogical / catalog reference (opaque ids only)."""

    ref_id: str
    kind: str = "grammar_topic"
    label: LocalizedText = field(default_factory=LocalizedText)


@dataclass(frozen=True, slots=True)
class ExpectedOutputSpec:
    """One expected learner output channel."""

    output_id: str
    output_type: str  # ExpectedOutputType value or registered extension
    required: bool = True
    options: tuple[str, ...] = ()  # e.g. choice ids — opaque, not UI
    constraints: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CompletionRule:
    """Deterministic completion gate declaration (Runtime enforces later)."""

    rule_id: str
    kind: str  # e.g. require_all_outputs | min_correct | attempt_limit
    params: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvidenceDeclaration:
    """Evidence contract — Spec declares; Runtime emits; Mastery scores later."""

    evidence_id: str
    evidence_kind: str  # EvidenceKind value or registered extension
    grammar_targets: tuple[str, ...] = ()
    observation_types_hint: tuple[str, ...] = ()
    required: bool = True
    notes: str = ""


@dataclass(frozen=True, slots=True)
class ProviderMetadata:
    """Opaque provider provenance — executors must not depend on internals."""

    provider_id: str = ""
    provider_version: str = ""
    generation_mode: str = ""  # template | cached | stub | ...
    extras: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ActivityVersionSet:
    """Replayability / versioning bundle."""

    activity_schema_version: int = ACTIVITY_SCHEMA_VERSION
    provider_version: str = ""
    planner_version: str = ""
    blueprint_version: str = ""
    catalog_version: str = ""
    grammar_schema_version: int = GRAMMAR_SCHEMA_VERSION
    package_version: str = ACTIVITY_SPEC_PACKAGE_VERSION


@dataclass(frozen=True, slots=True)
class ActivitySpecification:
    """Canonical activity format for EduMind Grammar activities.

    Never contains UI trees, Runtime session state, or arbitrary markdown documents.
    Structured fields only — renderers project these later.
    """

    activity_id: str
    activity_type: str  # ActivityType value or registered extension
    grammar_topic: str
    lesson_id: str
    step_id: str
    title: LocalizedText
    goal: LocalizedText
    instructions: LocalizedText
    difficulty: ActivityDifficulty = ActivityDifficulty.guided
    estimated_duration_seconds: int = 0
    grammar_targets: tuple[str, ...] = ()
    expected_outputs: tuple[ExpectedOutputSpec, ...] = ()
    evaluation_mode: str = EvaluationMode.rule_based.value
    completion_rules: tuple[CompletionRule, ...] = ()
    hints: tuple[LocalizedText, ...] = ()
    assets: tuple[ActivityAssetRef, ...] = ()
    references: tuple[ActivityReference, ...] = ()
    evidence: tuple[EvidenceDeclaration, ...] = ()
    provider_metadata: ProviderMetadata = field(default_factory=ProviderMetadata)
    localization_default_locale: str = "en"
    supported_locales: tuple[str, ...] = ("en",)
    versions: ActivityVersionSet = field(default_factory=ActivityVersionSet)
    fingerprint: str = ""
    # Structured payload for type-specific data (choices, blanks, match pairs) — not markdown.
    payload: dict[str, str] = field(default_factory=dict)

    @property
    def activity_schema_version(self) -> int:
        return self.versions.activity_schema_version
