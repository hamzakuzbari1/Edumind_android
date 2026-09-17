"""Skill-facing completion bridge to Wave B pipeline (Wave C).

Skills must not import mastery/progression directly — only this facade.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
from app.services.language_grammar_pipeline.completion import (
    ActivityCompletionRequest,
    ActivityCompletionResult,
    apply_activity_completion_async,
)
from app.services.language_grammar_skill_context.builder import build_skill_grammar_context
from app.services.language_grammar_skill_context.guard import assert_grammar_id_matches
from app.services.language_grammar_skill_context.stamp import extract_stamped_grammar_id
from app.services.language_grammar_skill_context.types import SkillGrammarContextError


async def complete_skill_activity_async(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    grammar_id: str,
    skill: GrammarEvidenceSourceSkill | str,
    score: float,
    activity_id: str = "",
    activity_type: str = "",
    lesson_id: str = "",
    confidence: float | None = None,
    context: str = "",
    observation_id: str = "",
    stamped_grammar_id: str | None = None,
) -> ActivityCompletionResult:
    """Record evidence for a completed skill activity on the stamped grammar node.

    If ``stamped_grammar_id`` is provided, rejects drift away from the stamp.
    """
    gid = (grammar_id or "").strip().lower()
    if stamped_grammar_id:
        gid = assert_grammar_id_matches(
            stamped=stamped_grammar_id,
            claimed=gid,
            allow_missing_claim=False,
        )
    if not gid:
        raise SkillGrammarContextError(
            "missing_grammar_id",
            "Completed skill activity requires a stamped grammar_id",
        )
    return await apply_activity_completion_async(
        db,
        ActivityCompletionRequest(
            student_id=student_id,
            language_id=language_id,
            grammar_id=gid,
            skill=skill,
            score=score,
            activity_id=activity_id,
            activity_type=activity_type or (
                skill.value if isinstance(skill, GrammarEvidenceSourceSkill) else str(skill)
            ),
            lesson_id=lesson_id,
            confidence=confidence,
            context=context,
            observation_id=observation_id,
        ),
    )


async def complete_from_stamped_payload_async(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    skill: GrammarEvidenceSourceSkill | str,
    score: float,
    payload: dict | None,
    activity_id: str = "",
    activity_type: str = "",
    lesson_id: str = "",
    confidence: float | None = None,
    context: str = "",
    observation_id: str = "",
) -> ActivityCompletionResult | None:
    """Complete only when the activity body carries a grammar stamp; else no-op."""
    stamped = extract_stamped_grammar_id(payload)
    if not stamped:
        return None
    return await complete_skill_activity_async(
        db,
        student_id=student_id,
        language_id=language_id,
        grammar_id=stamped,
        skill=skill,
        score=score,
        activity_id=activity_id,
        activity_type=activity_type,
        lesson_id=lesson_id,
        confidence=confidence,
        context=context,
        observation_id=observation_id,
        stamped_grammar_id=stamped,
    )


async def complete_current_skill_activity_async(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    skill: GrammarEvidenceSourceSkill | str,
    score: float,
    activity_id: str = "",
    activity_type: str = "",
    lesson_id: str = "",
    confidence: float | None = None,
    context: str = "",
    observation_id: str = "",
    require_passing_score: bool = True,
) -> ActivityCompletionResult | None:
    """Record a passed skill activity against the server-selected current grammar target.

    Existing skill pages may not carry a per-activity grammar stamp yet. This
    bridge still keeps grammar ownership server-side by using the resolver.
    """
    score_value = max(0.0, min(100.0, float(score)))
    if require_passing_score and score_value < 70.0:
        return None
    grammar_ctx = await build_skill_grammar_context(
        db,
        student_id=student_id,
        language_id=language_id,
        source_skill=skill,
    )
    if grammar_ctx is None:
        return None
    return await complete_skill_activity_async(
        db,
        student_id=student_id,
        language_id=language_id,
        grammar_id=grammar_ctx.grammar_id,
        skill=skill,
        score=score_value,
        activity_id=activity_id,
        activity_type=activity_type,
        lesson_id=lesson_id,
        confidence=confidence,
        context=context,
        observation_id=observation_id,
        stamped_grammar_id=grammar_ctx.grammar_id,
    )
