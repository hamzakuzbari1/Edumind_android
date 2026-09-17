"""Canonical speaking educational mission taxonomy + legality boundary (S10.1).

The taxonomy is no longer defaults-only. Each educational mission kind (dimension A)
declares:
- the set of LEGAL execution modes (dimension B)
- the set of LEGAL evidence intents (dimension C)
- a canonical default for each dimension
- teaches / assesses / executability flags

`validate_mission_combination()` is the single canonical legality boundary. It is
invoked by the `SpeakingEducationalMission` dataclass invariant, so every construction
(including storage deserialization) is validated. Callers must not scatter their own
combination checks.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_speaking.enums import (
    SpeakingEvidenceIntent,
    SpeakingExecutionMode,
    SpeakingMissionKind,
)

TAXONOMY_VERSION = "10.1.0"


@dataclass(frozen=True, slots=True)
class SpeakingTaxonomyEntry:
    """One row of the canonical mission taxonomy matrix."""

    mission_kind: SpeakingMissionKind
    legal_execution_modes: frozenset[SpeakingExecutionMode]
    legal_evidence_intents: frozenset[SpeakingEvidenceIntent]
    default_execution_mode: SpeakingExecutionMode
    default_evidence_intent: SpeakingEvidenceIntent
    teaches: bool
    assesses: bool
    can_bear_task: bool  # may contain one or more executable tasks
    content_bearing: bool  # carries teaching/review content blocks

    def to_dict(self) -> dict[str, object]:
        return {
            "mission_kind": self.mission_kind.value,
            "legal_execution_modes": sorted(m.value for m in self.legal_execution_modes),
            "legal_evidence_intents": sorted(i.value for i in self.legal_evidence_intents),
            "default_execution_mode": self.default_execution_mode.value,
            "default_evidence_intent": self.default_evidence_intent.value,
            "teaches": self.teaches,
            "assesses": self.assesses,
            "can_bear_task": self.can_bear_task,
            "content_bearing": self.content_bearing,
        }


_EM = SpeakingExecutionMode
_EI = SpeakingEvidenceIntent
_MK = SpeakingMissionKind


SPEAKING_MISSION_TAXONOMY: dict[SpeakingMissionKind, SpeakingTaxonomyEntry] = {
    _MK.teaching: SpeakingTaxonomyEntry(
        mission_kind=_MK.teaching,
        legal_execution_modes=frozenset({_EM.study}),
        legal_evidence_intents=frozenset({_EI.none}),
        default_execution_mode=_EM.study,
        default_evidence_intent=_EI.none,
        teaches=True,
        assesses=False,
        can_bear_task=False,
        content_bearing=True,
    ),
    _MK.noticing: SpeakingTaxonomyEntry(
        mission_kind=_MK.noticing,
        legal_execution_modes=frozenset({_EM.study, _EM.controlled_response}),
        legal_evidence_intents=frozenset({_EI.none, _EI.formative}),
        default_execution_mode=_EM.study,
        default_evidence_intent=_EI.none,
        teaches=True,
        assesses=False,
        can_bear_task=True,
        content_bearing=True,
    ),
    _MK.guided_practice: SpeakingTaxonomyEntry(
        mission_kind=_MK.guided_practice,
        legal_execution_modes=frozenset({_EM.controlled_response}),
        legal_evidence_intents=frozenset({_EI.formative}),
        default_execution_mode=_EM.controlled_response,
        default_evidence_intent=_EI.formative,
        teaches=True,
        assesses=True,
        can_bear_task=True,
        content_bearing=True,
    ),
    _MK.speak: SpeakingTaxonomyEntry(
        mission_kind=_MK.speak,
        legal_execution_modes=frozenset({_EM.recorded_response, _EM.live_evi_conversation}),
        legal_evidence_intents=frozenset({_EI.formative, _EI.summative}),
        default_execution_mode=_EM.live_evi_conversation,
        default_evidence_intent=_EI.summative,
        teaches=False,
        assesses=True,
        can_bear_task=True,
        content_bearing=False,
    ),
    _MK.feedback: SpeakingTaxonomyEntry(
        mission_kind=_MK.feedback,
        legal_execution_modes=frozenset({_EM.study, _EM.review}),
        legal_evidence_intents=frozenset({_EI.none}),
        default_execution_mode=_EM.review,
        default_evidence_intent=_EI.none,
        teaches=True,
        assesses=False,
        can_bear_task=False,
        content_bearing=True,
    ),
    _MK.transfer: SpeakingTaxonomyEntry(
        mission_kind=_MK.transfer,
        legal_execution_modes=frozenset({_EM.recorded_response, _EM.live_evi_conversation}),
        legal_evidence_intents=frozenset({_EI.transfer}),
        default_execution_mode=_EM.recorded_response,
        default_evidence_intent=_EI.transfer,
        teaches=False,
        assesses=True,
        can_bear_task=True,
        content_bearing=False,
    ),
    _MK.retention_review: SpeakingTaxonomyEntry(
        mission_kind=_MK.retention_review,
        legal_execution_modes=frozenset({_EM.review, _EM.recorded_response, _EM.live_evi_conversation}),
        legal_evidence_intents=frozenset({_EI.none, _EI.retention}),
        default_execution_mode=_EM.review,
        default_evidence_intent=_EI.retention,
        teaches=False,
        assesses=True,
        can_bear_task=True,
        content_bearing=True,
    ),
}


def taxonomy_entry(kind: SpeakingMissionKind) -> SpeakingTaxonomyEntry:
    return SPEAKING_MISSION_TAXONOMY[kind]


def taxonomy_is_complete() -> bool:
    """Every mission kind has exactly one canonical taxonomy row."""
    return set(SPEAKING_MISSION_TAXONOMY.keys()) == set(SpeakingMissionKind)


def is_legal_mission_combination(
    kind: SpeakingMissionKind,
    execution_mode: SpeakingExecutionMode,
    evidence_intent: SpeakingEvidenceIntent,
) -> bool:
    entry = SPEAKING_MISSION_TAXONOMY.get(kind)
    if entry is None:
        return False
    return execution_mode in entry.legal_execution_modes and evidence_intent in entry.legal_evidence_intents


def validate_mission_combination(
    kind: SpeakingMissionKind,
    execution_mode: SpeakingExecutionMode,
    evidence_intent: SpeakingEvidenceIntent,
) -> None:
    """Single canonical legality boundary — raises ValueError on illegal triples."""
    entry = SPEAKING_MISSION_TAXONOMY.get(kind)
    if entry is None:
        raise ValueError(f"unknown_mission_kind:{kind}")
    if execution_mode not in entry.legal_execution_modes:
        legal = sorted(m.value for m in entry.legal_execution_modes)
        raise ValueError(
            f"illegal_execution_mode_for_mission:{kind.value}+{execution_mode.value} (legal: {legal})"
        )
    if evidence_intent not in entry.legal_evidence_intents:
        legal = sorted(i.value for i in entry.legal_evidence_intents)
        raise ValueError(
            f"illegal_evidence_intent_for_mission:{kind.value}+{evidence_intent.value} (legal: {legal})"
        )
