"""Shared grammar context for skill generators (Wave C)."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_grammar.enums import (
    GrammarCEFRBand,
    GrammarEvidenceSourceSkill,
    GrammarReinforcementSkill,
)


@dataclass(frozen=True, slots=True)
class SkillGrammarContext:
    """Single grammar context object shared by Reading/Listening/Speaking/Writing/Vocabulary.

    Built ONLY via the Grammar Target Resolver + curriculum catalog metadata.
    Skills must not invent or override grammar_id.
    """

    grammar_id: str
    display_code: str
    display_name: str
    cefr_band: GrammarCEFRBand
    source_skill: GrammarEvidenceSourceSkill
    grammar_targets: tuple[str, ...] = ()
    learning_objectives: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    common_mistakes: tuple[str, ...] = ()
    teaching_notes: str = ""
    focus_note: str = ""
    reinforcement_skills: tuple[GrammarReinforcementSkill, ...] = ()
    recommended_contexts: tuple[str, ...] = ()
    vocabulary_reinforcement: bool = False
    secondary_grammar_ids: tuple[str, ...] = ()

    def prompt_block(self) -> str:
        """Stable grammar instruction block for all skill generators."""
        targets = ", ".join(self.grammar_targets) or self.display_name
        examples = "; ".join(self.examples[:3])
        mistakes = "; ".join(self.common_mistakes[:3])
        notes = self.teaching_notes or self.focus_note
        lines = [
            "GRAMMAR TARGET (authoritative — do not change):",
            f"- grammar_id: {self.grammar_id}",
            f"- display_code: {self.display_code}",
            f"- title: {self.display_name}",
            f"- CEFR: {self.cefr_band.value}",
            f"- patterns/targets: {targets}",
        ]
        if notes:
            lines.append(f"- teaching_notes: {notes}")
        if examples:
            lines.append(f"- examples: {examples}")
        if mistakes:
            lines.append(f"- common_mistakes: {mistakes}")
        if self.vocabulary_reinforcement:
            lines.append(
                "- vocabulary: generate lexical support that reinforces this grammar "
                "(collocations / high-frequency forms)."
            )
        else:
            lines.append(
                "- vocabulary: keep lexical support light; do not invent a separate vocab curriculum."
            )
        lines.append(
            "All activity content and questions MUST exercise this grammar only. "
            "Do not introduce a different grammar topic."
        )
        return "\n".join(lines)

    def as_stamp_dict(self) -> dict[str, object]:
        return {
            "grammar_id": self.grammar_id,
            "display_code": self.display_code,
            "grammar_title": self.display_name,
            "grammar_cefr": self.cefr_band.value,
            "grammar_targets": list(self.grammar_targets),
            "grammar_source_skill": self.source_skill.value,
            "grammar_vocabulary_reinforcement": self.vocabulary_reinforcement,
        }


@dataclass(frozen=True, slots=True)
class SkillGrammarStamp:
    """Minimal stamp persisted on skill activity bodies."""

    grammar_id: str
    display_code: str = ""
    source_skill: str = ""


class SkillGrammarContextError(ValueError):
    """Raised when a skill bypasses or contradicts the resolver stamp."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")
