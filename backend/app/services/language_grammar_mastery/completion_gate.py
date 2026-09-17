"""Strict cross-skill gate before a grammar topic can unlock the next topic."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
from app.services.language_grammar_mastery.types import GrammarMasteryRecord


REQUIRED_GRAMMAR_PRACTICE_CORRECT = 14
REQUIRED_SKILL_PASS_SCORE = 70.0
REQUIRED_TRANSFER_SKILLS = (
    GrammarEvidenceSourceSkill.reading.value,
    GrammarEvidenceSourceSkill.listening.value,
    GrammarEvidenceSourceSkill.writing.value,
    GrammarEvidenceSourceSkill.speaking.value,
)


@dataclass(frozen=True, slots=True)
class GrammarCompletionGateStatus:
    grammar_lesson_complete: bool
    completed_skill_names: tuple[str, ...]
    missing_skill_names: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return self.grammar_lesson_complete and not self.missing_skill_names


def completion_gate_status(record: GrammarMasteryRecord) -> GrammarCompletionGateStatus:
    scores = dict(record.best_score_by_skill or {})
    attempts = dict(record.best_attempt_count_by_skill or {})
    correct = dict(record.best_correct_count_by_skill or {})

    grammar_score = float(scores.get(GrammarEvidenceSourceSkill.grammar_lesson.value) or 0.0)
    grammar_attempts = int(attempts.get(GrammarEvidenceSourceSkill.grammar_lesson.value) or 0)
    grammar_correct = int(correct.get(GrammarEvidenceSourceSkill.grammar_lesson.value) or 0)
    grammar_lesson_complete = (
        grammar_score >= 99.5
        and grammar_attempts >= REQUIRED_GRAMMAR_PRACTICE_CORRECT
        and grammar_correct >= REQUIRED_GRAMMAR_PRACTICE_CORRECT
    )

    completed = tuple(
        skill for skill in REQUIRED_TRANSFER_SKILLS if float(scores.get(skill) or 0.0) >= REQUIRED_SKILL_PASS_SCORE
    )
    missing = tuple(skill for skill in REQUIRED_TRANSFER_SKILLS if skill not in completed)
    return GrammarCompletionGateStatus(
        grammar_lesson_complete=grammar_lesson_complete,
        completed_skill_names=completed,
        missing_skill_names=missing,
    )


def completion_gate_ready(record: GrammarMasteryRecord) -> bool:
    return completion_gate_status(record).ready
