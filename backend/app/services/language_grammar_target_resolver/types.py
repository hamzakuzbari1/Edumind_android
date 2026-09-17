"""Types for the Grammar Target Resolver — sole skill Runtime entry for targets."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_grammar.enums import GrammarCEFRBand, GrammarEvidenceSourceSkill


@dataclass(frozen=True, slots=True)
class GrammarTargetMeta:
    """Lightweight topic meta stamped into skill packages/sessions."""

    grammar_id: str
    display_code: str
    display_name: str
    cefr_band: GrammarCEFRBand


@dataclass(frozen=True, slots=True)
class GrammarTargetResolveRequest:
    """Skill Runtime request for grammar targets (never invents IDs)."""

    student_id: int
    language_id: int
    source_skill: GrammarEvidenceSourceSkill
    max_targets: int = 2
    prefer_current: bool = True


@dataclass(frozen=True, slots=True)
class GrammarTargetResolution:
    """Resolved grammar targets for skill constraints (read-only)."""

    grammar_ids: tuple[str, ...]
    display_codes: tuple[str, ...]
    topics: tuple[GrammarTargetMeta, ...]
    current_grammar_id: str | None
    current_display_code: str | None
    anchor_cefr: GrammarCEFRBand
    source_skill: GrammarEvidenceSourceSkill
