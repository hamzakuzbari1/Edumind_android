"""Persist generated writing lessons and audit metadata (W6)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.services.language_writing.enums import OfficialWritingCEFR
from app.services.language_writing_generation import (
    WRITING_BLUEPRINT_KEY,
    WRITING_CURRICULUM_KEY,
    WRITING_GENERATION_KEY,
    WRITING_GOAL_KEY,
)
from app.services.language_writing_generation.audit_types import WritingGenerationAuditRecord
from app.services.language_writing_generation.canonical_lesson_types import WritingCanonicalGeneratedLesson
from app.services.language_writing_lesson_planner.types import WritingLessonBlueprint
from app.services.language_writing_runtime.types import RUNTIME_SCHEMA_VERSION

CONTENT_TYPE = "writing_prompt"
SOURCE_TAG = "writing_runtime_v6"


def _level_from_cefr(cefr: OfficialWritingCEFR) -> LanguageLevel:
    return LanguageLevel(cefr.value)


def build_audit_persistence(
    audit: WritingGenerationAuditRecord,
    *,
    model_name: str,
    provider_name: str,
    runtime_version: str = RUNTIME_SCHEMA_VERSION,
) -> dict[str, object]:
    """Extend W5 audit dict with W6 runtime provider fields."""
    payload = audit.to_persistence_dict()
    payload["model_name"] = model_name
    payload["provider_name"] = provider_name
    payload["runtime_version"] = runtime_version
    return payload


def build_body_json(
    *,
    student_id: int | None = None,
    blueprint: WritingLessonBlueprint,
    canonical: WritingCanonicalGeneratedLesson,
    audit: WritingGenerationAuditRecord,
    model_name: str,
    provider_name: str,
    selection_metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    """Assemble stored body_json for LanguageContentItem."""
    curriculum = {
        "official_cefr": blueprint.official_cefr.value,
        "arc_stage": blueprint.curriculum_arc.value,
        "topic_id": blueprint.topic_id.value,
        "chain_id": blueprint.chain_id,
        "chain_node_id": blueprint.chain_node_id,
        "chain_position": blueprint.chain_position,
        "context_complexity": int(blueprint.context_complexity),
    }
    if selection_metadata:
        curriculum.update(selection_metadata)
    payload: dict[str, object] = {
        "prompt": canonical.writing_prompt,
        "mission_title": canonical.mission_title,
        "writing_context": canonical.writing_context,
        "instructions": list(canonical.instructions),
        "checklist": list(canonical.checklist),
        "tips": list(canonical.tips),
        "learning_outcomes": list(canonical.learning_outcomes),
        "success_criteria": list(canonical.success_criteria),
        "constraints": list(canonical.constraints),
        "expected_output": canonical.expected_output,
        "grammar_display": canonical.grammar_display,
        "vocabulary_display": canonical.vocabulary_display,
        "min_words": blueprint.success_criteria.min_words,
        "max_words": blueprint.success_criteria.max_words,
        "min_sentences": max(2, blueprint.success_criteria.min_words // 15),
        "source": SOURCE_TAG,
        "runtime_version": RUNTIME_SCHEMA_VERSION,
        WRITING_GOAL_KEY: blueprint.personal_goal.value,
        WRITING_BLUEPRINT_KEY: blueprint.to_dict(),
        WRITING_CURRICULUM_KEY: curriculum,
        WRITING_GENERATION_KEY: build_audit_persistence(
            audit,
            model_name=model_name,
            provider_name=provider_name,
        ),
        "canonical_lesson": canonical.to_dict(),
    }
    if student_id is not None:
        payload["owner_student_id"] = student_id
    return payload


async def persist_generated_writing_lesson(
    db: AsyncSession,
    *,
    language_id: int,
    student_id: int,
    blueprint: WritingLessonBlueprint,
    canonical: WritingCanonicalGeneratedLesson,
    audit: WritingGenerationAuditRecord,
    model_name: str,
    provider_name: str,
    selection_metadata: dict[str, object] | None = None,
) -> LanguageContentItem:
    """Store generated lesson for student — audit metadata under writing_generation."""
    item_kwargs = dict(
        language_id=language_id,
        skill=LanguageSkill.writing,
        level=_level_from_cefr(blueprint.official_cefr),
        content_type=CONTENT_TYPE,
        title=canonical.mission_title[:500],
        body_json=build_body_json(
            student_id=student_id,
            blueprint=blueprint,
            canonical=canonical,
            audit=audit,
            model_name=model_name,
            provider_name=provider_name,
            selection_metadata=selection_metadata,
        ),
        is_published=True,
    )
    if hasattr(LanguageContentItem, "student_id"):
        item_kwargs["student_id"] = student_id
    item = LanguageContentItem(**item_kwargs)
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item
