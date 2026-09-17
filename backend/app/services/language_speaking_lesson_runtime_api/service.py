"""Thin API twin for Speaking Lesson Runtime (E2)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.language_speaking_lesson_runtime import LessonRuntimeOut
from app.services.language_speaking_lesson_runtime.engine import (
    LessonRuntimeError,
    LessonRuntimeView,
    advance_lesson_section,
    get_lesson_runtime_view,
    mark_mini_prep_complete,
    mark_teaching_block_viewed,
    mark_vocabulary_viewed,
    open_lesson_runtime,
)


class LessonRuntimeApiError(Exception):
    def __init__(self, status_code: int, detail: str, code: str = "") -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(detail)


def _map_error(exc: LessonRuntimeError) -> LessonRuntimeApiError:
    status = {
        "not_found": 404,
        "no_package": 404,
        "no_runtime": 404,
        "no_progression": 404,
        "not_frozen": 409,
        "fingerprint_mismatch": 409,
        "mini_prep_required": 409,
        "unknown_vocab": 400,
        "unknown_block": 400,
        "corrupt": 422,
    }.get(exc.code, 400)
    return LessonRuntimeApiError(status, exc.message, exc.code)


def _out(view: LessonRuntimeView) -> LessonRuntimeOut:
    return LessonRuntimeOut(**view.to_dict())


def idle_lesson_runtime_api() -> LessonRuntimeOut:
    return LessonRuntimeOut(
        runtime_version="2.0.0",
        state={
            "schema_version": "2.0.0",
            "package_id": None,
            "content_item_id": None,
            "constraints_fingerprint": "",
            "content_fingerprint": "",
            "current_section": "not_started",
            "completed_sections": [],
            "viewed_vocabulary_ids": [],
            "completed_teaching_block_ids": [],
            "mini_practice_prep_done": False,
            "ready_for_discussion": False,
            "position_hint": "not_started",
            "started_at": "",
            "updated_at": "",
            "status": "idle",
        },
        package={},
        constraints_summary={},
        section_progress={
            "sections": [],
            "current": "not_started",
            "completed": [],
            "percent": 0,
            "ready_for_discussion": False,
        },
    )


async def open_lesson_runtime_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package_id: str | None = None,
    force_restart: bool = False,
) -> LessonRuntimeOut:
    try:
        view = await open_lesson_runtime(
            db,
            student_id=student_id,
            language_id=language_id,
            package_id=package_id,
            force_restart=force_restart,
        )
    except LessonRuntimeError as exc:
        raise _map_error(exc) from exc
    return _out(view)


async def get_lesson_runtime_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> LessonRuntimeOut:
    try:
        view = await get_lesson_runtime_view(
            db, student_id=student_id, language_id=language_id
        )
    except LessonRuntimeError as exc:
        if exc.code in {"no_runtime", "no_package", "not_found"}:
            return idle_lesson_runtime_api()
        raise _map_error(exc) from exc
    return _out(view)


async def advance_lesson_runtime_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> LessonRuntimeOut:
    try:
        view = await advance_lesson_section(
            db, student_id=student_id, language_id=language_id
        )
    except LessonRuntimeError as exc:
        raise _map_error(exc) from exc
    return _out(view)


async def mark_vocab_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    vocabulary_id: str,
) -> LessonRuntimeOut:
    try:
        view = await mark_vocabulary_viewed(
            db,
            student_id=student_id,
            language_id=language_id,
            vocabulary_id=vocabulary_id,
        )
    except LessonRuntimeError as exc:
        raise _map_error(exc) from exc
    return _out(view)


async def mark_block_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    block_id: str,
) -> LessonRuntimeOut:
    try:
        view = await mark_teaching_block_viewed(
            db,
            student_id=student_id,
            language_id=language_id,
            block_id=block_id,
        )
    except LessonRuntimeError as exc:
        raise _map_error(exc) from exc
    return _out(view)


async def mark_mini_prep_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> LessonRuntimeOut:
    try:
        view = await mark_mini_prep_complete(
            db, student_id=student_id, language_id=language_id
        )
    except LessonRuntimeError as exc:
        raise _map_error(exc) from exc
    return _out(view)
