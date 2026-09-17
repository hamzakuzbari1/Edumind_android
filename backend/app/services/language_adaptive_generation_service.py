"""Phase 7 — Adaptive Lesson Generation.

Builds the `[ADAPTIVE CONTEXT]` block injected (BEFORE the existing prompt) into on-demand content
generation, so each learner's generated lessons target THEM: pitched to their effective level
(Phase 3), gently reinforcing their weaknesses / recurring mistakes (Phase 2/3) and preferring their
interests (Phase 1). Reuses the existing services — no new tables, no new prompts replaced.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import language_difficulty_service as difficulty_service
from app.services import language_error_intelligence_service as error_service
from app.services import language_learner_memory_service as memory_service

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------------------
# Pure helper (no I/O — unit-tested directly)
# --------------------------------------------------------------------------------------------------
def format_adaptive_context(
    *,
    effective_level: str | None = None,
    interests: list[str] | None = None,
    weaknesses: list[str] | None = None,
    recent_errors: list[str] | None = None,
    preferred_types: list[str] | None = None,
) -> str:
    """The [ADAPTIVE CONTEXT] block. Returns "" when nothing is known (no injection)."""
    interests = interests or []
    weaknesses = weaknesses or []
    recent_errors = recent_errors or []
    preferred_types = preferred_types or []

    lines: list[str] = []
    if effective_level:
        lines.append(f"Effective level: {effective_level}")
    if weaknesses:
        lines.append(f"Primary weaknesses: {', '.join(weaknesses[:3])}")
    if recent_errors:
        lines.append(f"Recent recurring mistakes: {', '.join(recent_errors[:3])}")
    if interests:
        lines.append(f"Learner interests: {', '.join(interests[:5])}")
    if preferred_types:
        lines.append(f"Preferred activity types: {', '.join(preferred_types[:3])}")

    if not lines:
        return ""
    return (
        "[ADAPTIVE CONTEXT]\n"
        + "\n".join(lines)
        + "\nWeave these in naturally: pitch the difficulty to the effective level, gently target the "
        "weaknesses, and prefer the learner's interests for topics — without naming this context.\n"
        "[/ADAPTIVE CONTEXT]"
    )


# --------------------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------------------
async def build_adaptive_context(
    db: AsyncSession, *, student_id: int, language_id: int, skill: str
) -> str:
    """Assemble the [ADAPTIVE CONTEXT] block for a learner + skill. Best-effort: "" on any failure."""
    try:
        memory = await memory_service.get_memory(db, student_id=student_id, language_id=language_id)
        profile = await difficulty_service.calculate_modifier(
            db, student_id=student_id, language_id=language_id
        )
        skill = (skill or "").lower()
        if skill in difficulty_service.SKILL_DIMS:
            effective = difficulty_service.effective_label(
                profile.get("cefr_level") or "A1", (profile.get("modifiers") or {}).get(skill, 0.0)
            )
        else:
            effective = profile.get("effective_level") or profile.get("cefr_level")
        recent_errors = await error_service.top_issue_labels(
            db, student_id=student_id, language_id=language_id
        )
        weaknesses = memory.get("derived_weaknesses") or []
        block = format_adaptive_context(
            effective_level=effective,
            interests=memory.get("interests") or memory.get("favorite_topics"),
            weaknesses=weaknesses,
            recent_errors=recent_errors,
            preferred_types=memory.get("preferred_lesson_types"),
        )
        # Phase 9 integration: ground the top weakness in the CEFR grammar reference so the generated
        # content reinforces it ACCURATELY (text-based RAG; no pgvector).
        if block and (weaknesses or recent_errors):
            from app.services.language_curriculum_kb_service import get_prompt_grounding

            topic = (weaknesses[0] if weaknesses else recent_errors[0])
            grounding = get_prompt_grounding(topic, level=effective)
            if grounding:
                block = f"{block}\n\n{grounding}"
        return block
    except Exception:  # never let adaptive enrichment break content generation
        logger.warning("adaptive context build failed (student=%s)", student_id, exc_info=True)
        return ""
