"""Parse models for file-based grammar curriculum YAML (catalog-owned)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.language_grammar.enums import GrammarCEFRBand, GrammarReinforcementSkill
from app.services.language_grammar.id_canon import (
    assert_canonical_grammar_id,
    assert_grammar_display_code,
)
from app.services.language_grammar_catalog.types import GrammarEvidenceRequirements

# Final S12 English CEFR quotas (must sum to 53).
ENGLISH_CEFR_QUOTAS: dict[str, int] = {
    "A1": 13,
    "A2": 11,
    "B1": 11,
    "B2": 8,
    "C1": 6,
    "C2": 4,
}

EXPECTED_TOPIC_COUNT = sum(ENGLISH_CEFR_QUOTAS.values())


@dataclass(frozen=True, slots=True)
class CurriculumIndexDocument:
    version: str
    language_code: str
    schema_version: int
    ordered_grammar_ids: tuple[str, ...]
    cefr_quotas: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CurriculumTopicDocument:
    grammar_id: str
    display_code: str
    title: str
    cefr_level: str
    order: int
    prerequisites: tuple[str, ...] = ()
    unlock_targets: tuple[str, ...] = ()
    grammar_targets: tuple[str, ...] = ()
    teaching_notes: str = ""
    common_mistakes: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    learning_objectives: tuple[str, ...] = ()
    estimated_duration_minutes: int = 25
    difficulty: str = "guided"
    mastery_threshold: float = 80.0
    evidence: GrammarEvidenceRequirements = field(default_factory=GrammarEvidenceRequirements)
    reinforcement_skills: tuple[GrammarReinforcementSkill, ...] = ()
    recommended_contexts: tuple[str, ...] = ()
    minimum_context_diversity: int = 2
    review_priority: int = 3
    review_half_life_days: float = 14.0
    focus_note: str = ""


def _as_str_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    out: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            out.append(text)
    return tuple(out)


def _as_int(value: Any, *, field_name: str, default: int | None = None) -> int:
    if value is None:
        if default is None:
            raise ValueError(f"{field_name} is required")
        return int(default)
    return int(value)


def _as_float(value: Any, *, field_name: str, default: float | None = None) -> float:
    if value is None:
        if default is None:
            raise ValueError(f"{field_name} is required")
        return float(default)
    return float(value)


def parse_index_document(raw: dict[str, Any]) -> CurriculumIndexDocument:
    if not isinstance(raw, dict):
        raise ValueError("curriculum index must be a mapping")
    version = str(raw.get("version") or "").strip()
    language_code = str(raw.get("language_code") or raw.get("language") or "").strip().lower()
    schema_version = _as_int(raw.get("schema_version"), field_name="schema_version", default=1)
    ordered = _as_str_tuple(raw.get("ordered_grammar_ids") or raw.get("topics"), field_name="ordered_grammar_ids")
    if not version:
        raise ValueError("curriculum index version is required")
    if not language_code:
        raise ValueError("curriculum index language_code is required")
    if not ordered:
        raise ValueError("curriculum index ordered_grammar_ids must be non-empty")
    quotas_raw = raw.get("cefr_quotas") or {}
    if not isinstance(quotas_raw, dict):
        raise ValueError("cefr_quotas must be a mapping")
    quotas = {str(k).upper(): int(v) for k, v in quotas_raw.items()}
    return CurriculumIndexDocument(
        version=version,
        language_code=language_code,
        schema_version=schema_version,
        ordered_grammar_ids=tuple(assert_canonical_grammar_id(g) for g in ordered),
        cefr_quotas=quotas,
    )


def parse_topic_document(raw: dict[str, Any]) -> CurriculumTopicDocument:
    if not isinstance(raw, dict):
        raise ValueError("curriculum topic must be a mapping")
    grammar_id = assert_canonical_grammar_id(str(raw.get("grammar_id") or ""))
    display_code = assert_grammar_display_code(str(raw.get("display_code") or ""))
    title = str(raw.get("title") or raw.get("display_name") or "").strip()
    if not title:
        raise ValueError(f"{grammar_id}: title is required")
    cefr_level = str(raw.get("cefr_level") or raw.get("cefr_band") or "").strip().upper()
    if cefr_level not in GrammarCEFRBand.__members__:
        raise ValueError(f"{grammar_id}: invalid cefr_level {cefr_level!r}")
    order = _as_int(raw.get("order") or raw.get("introduction_order"), field_name="order")
    evidence_raw = raw.get("evidence") or {}
    if evidence_raw is None:
        evidence_raw = {}
    if not isinstance(evidence_raw, dict):
        raise ValueError(f"{grammar_id}: evidence must be a mapping")
    evidence = GrammarEvidenceRequirements(
        min_observations=_as_int(
            evidence_raw.get("min_observations"), field_name="evidence.min_observations", default=3
        ),
        min_distinct_contexts=_as_int(
            evidence_raw.get("min_distinct_contexts"),
            field_name="evidence.min_distinct_contexts",
            default=2,
        ),
        min_skills_covered=_as_int(
            evidence_raw.get("min_skills_covered"), field_name="evidence.min_skills_covered", default=1
        ),
    )
    skills_raw = _as_str_tuple(raw.get("reinforcement_skills"), field_name="reinforcement_skills")
    skills: list[GrammarReinforcementSkill] = []
    for skill in skills_raw:
        key = skill.strip().lower()
        if key not in GrammarReinforcementSkill.__members__:
            raise ValueError(f"{grammar_id}: unknown reinforcement skill {skill!r}")
        skills.append(GrammarReinforcementSkill(key))
    teaching_notes = str(raw.get("teaching_notes") or "").strip()
    focus_note = str(raw.get("focus_note") or teaching_notes or "").strip()
    return CurriculumTopicDocument(
        grammar_id=grammar_id,
        display_code=display_code,
        title=title,
        cefr_level=cefr_level,
        order=order,
        prerequisites=tuple(
            assert_canonical_grammar_id(p)
            for p in _as_str_tuple(raw.get("prerequisites"), field_name="prerequisites")
        ),
        unlock_targets=tuple(
            assert_canonical_grammar_id(p)
            for p in _as_str_tuple(raw.get("unlock_targets"), field_name="unlock_targets")
        ),
        grammar_targets=_as_str_tuple(raw.get("grammar_targets"), field_name="grammar_targets"),
        teaching_notes=teaching_notes,
        common_mistakes=_as_str_tuple(raw.get("common_mistakes"), field_name="common_mistakes"),
        examples=_as_str_tuple(raw.get("examples"), field_name="examples"),
        learning_objectives=_as_str_tuple(
            raw.get("learning_objectives"), field_name="learning_objectives"
        ),
        estimated_duration_minutes=_as_int(
            raw.get("estimated_duration_minutes"),
            field_name="estimated_duration_minutes",
            default=25,
        ),
        difficulty=str(raw.get("difficulty") or "guided").strip().lower(),
        mastery_threshold=_as_float(
            raw.get("mastery_threshold"), field_name="mastery_threshold", default=80.0
        ),
        evidence=evidence,
        reinforcement_skills=tuple(dict.fromkeys(skills)),
        recommended_contexts=_as_str_tuple(
            raw.get("recommended_contexts"), field_name="recommended_contexts"
        ),
        minimum_context_diversity=_as_int(
            raw.get("minimum_context_diversity"),
            field_name="minimum_context_diversity",
            default=2,
        ),
        review_priority=_as_int(raw.get("review_priority"), field_name="review_priority", default=3),
        review_half_life_days=_as_float(
            raw.get("review_half_life_days"), field_name="review_half_life_days", default=14.0
        ),
        focus_note=focus_note,
    )
