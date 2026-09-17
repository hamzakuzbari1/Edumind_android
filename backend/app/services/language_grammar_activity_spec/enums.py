"""Activity Specification enums & constants (G3.35).

Extensible via SpecRegistry — new types/modes require registration, not schema breaks.
"""

from __future__ import annotations

from enum import StrEnum

ACTIVITY_SCHEMA_VERSION = 1
ACTIVITY_SPEC_PACKAGE_VERSION = "1.0.0"
GRAMMAR_SCHEMA_VERSION = 1


class ActivityType(StrEnum):
    """Canonical activity kinds. New types register via SpecRegistry without breaking schema."""

    free_text = "free_text"
    multiple_choice = "multiple_choice"
    voice_recording = "voice_recording"
    ordering = "ordering"
    matching = "matching"
    fill_in_the_blank = "fill_in_the_blank"
    selection = "selection"
    conversation = "conversation"
    sentence_building = "sentence_building"
    # Extension slot — custom codes also allowed when registered.


class ExpectedOutputType(StrEnum):
    """Learner output modalities declared by a specification."""

    free_text = "free_text"
    multiple_choice = "multiple_choice"
    voice_recording = "voice_recording"
    ordering = "ordering"
    matching = "matching"
    fill_in_the_blank = "fill_in_the_blank"
    selection = "selection"
    conversation = "conversation"
    sentence_building = "sentence_building"


class EvaluationMode(StrEnum):
    """How the activity may be evaluated later — specification only, no execution."""

    manual = "manual"
    automatic = "automatic"
    llm_assisted = "llm_assisted"
    rule_based = "rule_based"
    hybrid = "hybrid"


class EvidenceKind(StrEnum):
    """Evidence kinds declared on the spec (Runtime emits later; Spec never scores mastery)."""

    formative = "formative"
    summative = "summative"
    transfer = "transfer"
    retention = "retention"
    observation = "observation"


class ActivityDifficulty(StrEnum):
    introductory = "introductory"
    guided = "guided"
    independent = "independent"
    challenge = "challenge"


# Built-in sets used to seed the SpecRegistry (mutable registry can grow).
BUILTIN_ACTIVITY_TYPES: frozenset[str] = frozenset(t.value for t in ActivityType)
BUILTIN_OUTPUT_TYPES: frozenset[str] = frozenset(t.value for t in ExpectedOutputType)
BUILTIN_EVALUATION_MODES: frozenset[str] = frozenset(m.value for m in EvaluationMode)
BUILTIN_EVIDENCE_KINDS: frozenset[str] = frozenset(k.value for k in EvidenceKind)
