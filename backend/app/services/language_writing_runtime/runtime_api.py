"""Writing runtime API service (W6) — student-facing generation entry point."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.language_writing_bundles import WritingGenerateOut
from app.services.language_progression_service import ensure_progression_row
from app.services.language_subscription_service import ensure_language_profile, get_default_language
from app.services.language_writing.enums import OfficialWritingCEFR, WritingGoal
from app.services.language_writing_runtime.generation_runtime import generate_writing_lesson
from app.services.language_writing_runtime.node_selection import select_node_for_student
from app.services.language_writing_runtime.student_context import (
    official_writing_cefr_for_student,
    writing_goal_from_preferences,
)


async def generate_writing_lesson_for_student(
    db: AsyncSession,
    *,
    student_id: int,
    goal: WritingGoal | None = None,
    chain_id: str | None = None,
    node_id: str | None = None,
    official_cefr: OfficialWritingCEFR | None = None,
) -> dict:
    language = await get_default_language(db)
    profile = await ensure_language_profile(db, student_id, language.id)
    resolved_goal = goal or writing_goal_from_preferences(profile.preferences_json)
    cefr = official_cefr or await official_writing_cefr_for_student(
        db, student_id=student_id, language_id=language.id
    )

    prog_row = await ensure_progression_row(db, student_id=student_id, language_id=language.id)
    prog_payload = dict(prog_row.promotion_readiness_json or {}) if prog_row else {}

    selection = await select_node_for_student(
        db,
        student_id=student_id,
        language_id=language.id,
        goal=resolved_goal,
        official_cefr=cefr,
        progression_payload=prog_payload,
        chain_id=chain_id,
        node_id=node_id,
    )

    if selection.node.official_cefr != cefr and not selection.remediation:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "cefr_mismatch",
                "message": f"Selected node CEFR {selection.node.official_cefr.value} does not match official {cefr.value}",
            },
        )

    result = await generate_writing_lesson(
        db,
        language_id=language.id,
        student_id=student_id,
        goal=resolved_goal,
        official_cefr=cefr,
        chain_id=selection.chain_id,
        node_id=selection.node_id,
        persist=True,
        selection_metadata=selection.recommendation.to_metadata(),
    )

    if not result.success:
        detail = result.error.to_dict() if result.error else {"message": "Writing generation failed"}
        code = status.HTTP_503_SERVICE_UNAVAILABLE if result.error and result.error.retryable else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=code, detail=detail)

    canonical = result.canonical_lesson
    blueprint = result.blueprint
    assert canonical is not None and blueprint is not None and result.content_item is not None

    payload = {
        "content_item_id": result.content_item.id,
        "title": canonical.mission_title,
        "prompt": canonical.writing_prompt,
        "mission_title": canonical.mission_title,
        "writing_context": canonical.writing_context,
        "instructions": list(canonical.instructions),
        "checklist": list(canonical.checklist),
        "learning_outcomes": list(canonical.learning_outcomes),
        "success_criteria": list(canonical.success_criteria),
        "expected_output": canonical.expected_output,
        "min_words": blueprint.success_criteria.min_words,
        "max_words": blueprint.success_criteria.max_words,
        "blueprint_hash": blueprint.blueprint_hash,
        "generation_hash": canonical.generation_hash,
        "outcome": result.outcome.value if result.outcome else None,
        "provider_name": result.provider.provider_name if result.provider else None,
        "model_name": result.provider.model_name if result.provider else None,
        "goal": resolved_goal.value,
        "official_cefr": cefr.value,
        "chain_id": selection.chain_id,
        "node_id": selection.node_id,
        "selection_reason": selection.recommendation.selection_reason,
        "runtime_version": result.runtime_version,
    }
    return WritingGenerateOut.model_validate(payload).model_dump()
