"""Types for Grammar Educational Package (G0).

Claude authors content from frozen constraints.
Claude never selects grammar_id, mastery, or Blueprint step order.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_grammar.enums import GrammarCEFRBand
from app.services.language_grammar_lesson_planner.types import GrammarLessonBlueprint


@dataclass(frozen=True, slots=True)
class GrammarPackageConstraints:
    """Frozen authoring constraints projected from a GrammarLessonBlueprint."""

    grammar_id: str
    label: str
    target_cefr: GrammarCEFRBand
    demonstration_forms: tuple[str, ...]
    objectives: tuple[str, ...]
    # Ordered step projection — Claude generates materials for these steps only.
    blueprint_steps: tuple[dict[str, str | bool | None], ...]
    recommended_contexts: tuple[str, ...] = ()
    focus_note: str = ""


@dataclass(frozen=True, slots=True)
class GrammarFrozenPackageRef:
    """Reference to a frozen Grammar educational package (persistence in G2)."""

    package_id: str
    grammar_id: str
    blueprint_fingerprint: str
    frozen_at: str | None = None


@dataclass(frozen=True, slots=True)
class GrammarPackageAuthoringInput:
    """Input bundle for G2 author pipeline."""

    blueprint: GrammarLessonBlueprint
    constraints: GrammarPackageConstraints
