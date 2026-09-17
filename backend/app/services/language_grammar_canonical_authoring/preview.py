"""Student-safe local preview projection for canonical grammar revisions."""

from __future__ import annotations

import copy
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.grammar_canonical_lesson import (
    GrammarCanonicalLesson,
    GrammarCanonicalLessonRevision,
)
from app.services.language_grammar_activity_authoring.llm.lesson_schema import (
    CANONICAL_LESSON_SCHEMA_VERSION,
    METHODOLOGY_VERSION,
)
from app.services.language_grammar_catalog.catalog import get_topic
from app.services.language_grammar_canonical_authoring.validation import (
    validate_persisted_revision_payload,
)
from app.services.language_grammar_canonical_lessons import GrammarCanonicalRevisionStatus

_SERVER_ONLY_STUDENT_KEYS = frozenset(
    {
        "server_teaching_metadata",
        "expected_answer",
        "sample_answer",
        "success_criteria",
        "misconception",
        "misconception_classification",
        "feedback_reasoning",
        "hint",
        "similar_retry_prompt",
        "validation_metadata",
        "remediation_routes",
    }
)


class GrammarCanonicalPreviewError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(code, message)


async def build_canonical_revision_preview_lesson(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
) -> dict[str, Any]:
    """Return the normal lesson envelope for a reviewable revision without writes."""
    revision = await db.get(GrammarCanonicalLessonRevision, revision_id)
    if revision is None:
        raise GrammarCanonicalPreviewError("revision_not_found", "Canonical grammar revision was not found")
    if revision.status != GrammarCanonicalRevisionStatus.REVIEWABLE.value:
        raise GrammarCanonicalPreviewError(
            "revision_not_reviewable",
            f"Only reviewable revisions can be previewed; got {revision.status!r}",
        )

    lesson = await db.get(GrammarCanonicalLesson, revision.lesson_id)
    if lesson is None:
        raise GrammarCanonicalPreviewError("canonical_lesson_not_found", "Revision parent lesson was not found")

    validation = validate_persisted_revision_payload(lesson=lesson, revision=revision)
    if not validation.valid:
        summary = validation.diagnostics_json or {}
        raise GrammarCanonicalPreviewError(
            "revision_payload_invalid",
            str(summary.get("code") or "Persisted revision failed canonical validation"),
        )

    return _project_revision_lesson(
        lesson=lesson,
        revision=revision,
        normalized_student_content=validation.normalized_student_content,
        lesson_id="canonical-review-preview",
        generation_mode="llm_canonical_grammar_lesson_authoring",
    )


async def build_canonical_lesson_start_package(
    db: AsyncSession,
    *,
    grammar_id: str,
    cefr_level: str,
    locale: str = "ar-SY",
    allow_reviewable: bool = False,
    allow_cefr_fallback: bool = False,
) -> dict[str, Any] | None:
    """Return a student-safe canonical lesson package for the normal start path.

    Published revisions are always preferred. In local development the caller may
    allow a reviewable revision so the real student UI can preview unpublished
    content without invoking Claude or exposing private metadata.
    """
    lesson_result = await db.execute(
        select(GrammarCanonicalLesson).where(
            GrammarCanonicalLesson.grammar_id == grammar_id,
            GrammarCanonicalLesson.cefr_level == cefr_level,
            GrammarCanonicalLesson.locale == locale,
            GrammarCanonicalLesson.methodology_version == METHODOLOGY_VERSION,
        )
    )
    lesson = lesson_result.scalar_one_or_none()
    if lesson is None and allow_cefr_fallback:
        lesson_result = await db.execute(
            select(GrammarCanonicalLesson)
            .where(
                GrammarCanonicalLesson.grammar_id == grammar_id,
                GrammarCanonicalLesson.locale == locale,
                GrammarCanonicalLesson.methodology_version == METHODOLOGY_VERSION,
            )
            .order_by(GrammarCanonicalLesson.created_at.desc())
            .limit(1)
        )
        lesson = lesson_result.scalar_one_or_none()
    if lesson is None:
        return None

    revision = await _latest_revision_for_start(
        db,
        lesson_id=lesson.id,
        allow_reviewable=allow_reviewable,
    )
    if revision is None:
        return None

    validation = validate_persisted_revision_payload(lesson=lesson, revision=revision)
    if not validation.valid:
        raise GrammarCanonicalPreviewError(
            "revision_payload_invalid",
            str((validation.diagnostics_json or {}).get("code") or "Persisted revision failed canonical validation"),
        )

    return _project_revision_lesson(
        lesson=lesson,
        revision=revision,
        normalized_student_content=validation.normalized_student_content,
        lesson_id=f"canonical-{revision.id}",
        generation_mode="published_canonical_grammar_lesson"
        if revision.status == GrammarCanonicalRevisionStatus.PUBLISHED.value
        else "reviewable_canonical_grammar_lesson",
    )


async def _latest_revision_for_start(
    db: AsyncSession,
    *,
    lesson_id: uuid.UUID,
    allow_reviewable: bool,
) -> GrammarCanonicalLessonRevision | None:
    published = await db.execute(
        select(GrammarCanonicalLessonRevision)
        .where(
            GrammarCanonicalLessonRevision.lesson_id == lesson_id,
            GrammarCanonicalLessonRevision.status == GrammarCanonicalRevisionStatus.PUBLISHED.value,
        )
        .order_by(GrammarCanonicalLessonRevision.revision_number.desc())
        .limit(1)
    )
    revision = published.scalar_one_or_none()
    if revision is not None or not allow_reviewable:
        return revision

    reviewable = await db.execute(
        select(GrammarCanonicalLessonRevision)
        .where(
            GrammarCanonicalLessonRevision.lesson_id == lesson_id,
            GrammarCanonicalLessonRevision.status == GrammarCanonicalRevisionStatus.REVIEWABLE.value,
        )
        .order_by(GrammarCanonicalLessonRevision.revision_number.desc())
        .limit(1)
    )
    return reviewable.scalar_one_or_none()


def _project_revision_lesson(
    *,
    lesson: GrammarCanonicalLesson,
    revision: GrammarCanonicalLessonRevision,
    normalized_student_content: dict[str, Any] | None,
    lesson_id: str,
    generation_mode: str,
) -> dict[str, Any]:
    student_content = copy.deepcopy(normalized_student_content or revision.student_content_json or {})
    _assert_student_content_safe(student_content)

    display_name = _display_name_for_lesson(lesson)
    lesson_goal = _lesson_goal(student_content)
    return {
        "lesson_id": lesson_id,
        "lesson_schema_version": revision.schema_version or CANONICAL_LESSON_SCHEMA_VERSION,
        "methodology_version": lesson.methodology_version,
        "revision_id": str(revision.id),
        "canonical_revision_id": str(revision.id),
        "grammar_id": lesson.grammar_id,
        "display_name": display_name,
        "cefr_level": lesson.cefr_level,
        "grammar_target": lesson.grammar_id,
        "lesson_title": display_name,
        "student_content": student_content,
        "teacher_opening": "",
        "lesson_goal": lesson_goal,
        "warmup": "",
        "main_activity": "",
        "follow_up_questions": [],
        "common_mistakes": [],
        "expected_patterns": [],
        "completion_message": "",
        "estimated_minutes": 10,
        "difficulty": "guided",
        "pipeline_id": "",
        "activity_id": "",
        "generation_mode": generation_mode,
        "authoring_status": "ready",
        "retry_message": "",
        "activity_session_id": "",
    }


def _display_name_for_lesson(lesson: GrammarCanonicalLesson) -> str:
    topic = get_topic(lesson.grammar_id)
    if topic is not None and topic.display_name:
        return topic.display_name
    return lesson.grammar_id.replace("gram_", "").replace("_", " ").title()


def _lesson_goal(student_content: dict[str, Any]) -> str:
    meaning_hook = student_content.get("meaning_hook") or {}
    reflection = student_content.get("reflection") or {}
    return str(meaning_hook.get("why_it_matters") or reflection.get("summary") or "")


def _assert_student_content_safe(value: Any, *, path: str = "student_content") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _SERVER_ONLY_STUDENT_KEYS:
                raise GrammarCanonicalPreviewError(
                    "private_field_in_student_content",
                    f"Student preview contains server-only key at {path}.{key}",
                )
            _assert_student_content_safe(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_student_content_safe(child, path=f"{path}[{index}]")
