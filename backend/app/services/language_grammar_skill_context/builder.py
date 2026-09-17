"""Build SkillGrammarContext via Target Resolver + curriculum metadata (Wave C)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_grammar.enums import (
    GrammarEvidenceSourceSkill,
    GrammarReinforcementSkill,
)
from app.services.language_grammar_catalog.catalog import get_topic
from app.services.language_grammar_skill_context.types import (
    SkillGrammarContext,
    SkillGrammarContextError,
)
from app.services.language_grammar_target_resolver import (
    GrammarTargetResolveRequest,
    resolve,
)


def _coerce_skill(skill: GrammarEvidenceSourceSkill | str) -> GrammarEvidenceSourceSkill:
    if isinstance(skill, GrammarEvidenceSourceSkill):
        return skill
    key = str(skill or "").strip().lower()
    if key == "grammar":
        key = "grammar_lesson"
    try:
        return GrammarEvidenceSourceSkill(key)
    except ValueError as exc:
        raise SkillGrammarContextError(
            "invalid_source_skill",
            f"Unsupported skill for grammar context: {skill!r}",
        ) from exc


def context_from_grammar_id(
    grammar_id: str,
    *,
    source_skill: GrammarEvidenceSourceSkill | str,
    secondary_grammar_ids: tuple[str, ...] = (),
) -> SkillGrammarContext:
    """Build context from a resolver-chosen grammar_id (no independent selection)."""
    skill = _coerce_skill(source_skill)
    topic = get_topic(grammar_id)
    if topic is None:
        raise SkillGrammarContextError(
            "unknown_grammar_id",
            f"Resolver returned unknown grammar_id: {grammar_id}",
        )
    reinforcement = tuple(topic.best_reinforcement_skills)
    vocab_ok = GrammarReinforcementSkill.vocabulary in reinforcement
    return SkillGrammarContext(
        grammar_id=topic.grammar_id,
        display_code=topic.display_code,
        display_name=topic.display_name,
        cefr_band=topic.cefr_band,
        source_skill=skill,
        grammar_targets=tuple(topic.demonstration_patterns),
        learning_objectives=tuple(topic.learning_objectives),
        examples=tuple(topic.example_sentences),
        common_mistakes=tuple(topic.common_errors),
        teaching_notes=topic.teaching_notes or topic.focus_note,
        focus_note=topic.focus_note,
        reinforcement_skills=reinforcement,
        recommended_contexts=tuple(topic.recommended_contexts),
        vocabulary_reinforcement=vocab_ok,
        secondary_grammar_ids=tuple(secondary_grammar_ids),
    )


async def build_skill_grammar_context(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
    source_skill: GrammarEvidenceSourceSkill | str,
    max_targets: int = 1,
    prefer_current: bool = True,
) -> SkillGrammarContext | None:
    """Resolver-first grammar context for skill generation.

    Returns None when the resolver has no current/candidate grammar (skills must
    not invent a substitute). Never skips the resolver call.
    """
    skill = _coerce_skill(source_skill)
    resolution = await resolve(
        db,
        GrammarTargetResolveRequest(
            student_id=student_id,
            language_id=language_id,
            source_skill=skill,
            max_targets=max(1, int(max_targets)),
            prefer_current=prefer_current,
        ),
    )
    primary = resolution.current_grammar_id or (
        resolution.grammar_ids[0] if resolution.grammar_ids else None
    )
    if not primary:
        return None
    secondary = tuple(gid for gid in resolution.grammar_ids if gid != primary)
    return context_from_grammar_id(
        primary,
        source_skill=skill,
        secondary_grammar_ids=secondary,
    )
