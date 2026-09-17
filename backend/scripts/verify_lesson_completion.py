"""Verify Phase 10.3 lesson completion rules."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models.progress import StudentLessonProgress
from app.services.lesson_completion_service import (
    get_or_create_progress,
    progress_to_dict,
    requirements_met,
    lesson_requirements,
    update_lesson_progress,
    try_finalize_completion,
    VIDEO_COMPLETION_THRESHOLD,
)
from app.services.lesson_capabilities import build_lesson_capabilities
from app.models.lesson import Lesson


async def main() -> None:
    async with AsyncSessionLocal() as db:
        cols = await db.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'student_lesson_progress'
                ORDER BY column_name
                """
            )
        )
        col_names = {r[0] for r in cols.all()}
        required = {
            "video_progress_percent",
            "pdf_progress_percent",
            "pdf_opened",
            "quiz_submitted",
            "updated_at",
            "completed_at",
        }
        missing = required - col_names
        if missing:
            print("FAIL: missing columns:", sorted(missing))
            sys.exit(1)
        print("OK: migration columns present")

        lesson = (
            await db.execute(
                select(Lesson)
                .where(Lesson.is_visible.is_(True))
                .options(selectinload(Lesson.assets))
                .limit(1)
            )
        ).scalar_one_or_none()
        if not lesson:
            print("SKIP: no visible lessons in DB")
            return

        student_id = 5
        progress = await get_or_create_progress(db, student_id, lesson.id)
        caps = await build_lesson_capabilities(db, lesson)
        reqs = lesson_requirements(caps)

        # Opening alone must not complete
        progress.completed_at = None
        progress.video_progress_percent = 0
        progress.pdf_progress_percent = 0
        progress.pdf_opened = False
        progress.quiz_submitted = False
        await db.flush()
        assert not requirements_met(progress, reqs) or not any(
            reqs[k] for k in ("requires_video", "requires_pdf", "requires_quiz")
        ), "empty progress should not meet requirements when content exists"
        print("OK: open-only does not complete")

        if reqs["requires_video"]:
            progress.video_progress_percent = VIDEO_COMPLETION_THRESHOLD - 1
            assert not requirements_met(progress, reqs), "89% video should not complete"
            progress.video_progress_percent = VIDEO_COMPLETION_THRESHOLD
            if not reqs["requires_quiz"] and not reqs["requires_pdf"]:
                assert requirements_met(progress, reqs), "90% video-only should complete"
            print("OK: video threshold rule")

        if reqs["requires_pdf"]:
            progress.pdf_opened = True
            progress.pdf_progress_percent = 99
            assert not requirements_met(progress, reqs), "99% PDF should not complete"
            progress.pdf_progress_percent = 100
            print("OK: PDF final-page rule")

        detail = await progress_to_dict(db, student_id, lesson.id, progress=progress, caps=caps)
        assert "completion_percent" in detail
        assert "requirements" in detail
        assert detail.get("newly_completed") is not True
        print("OK: progress_to_dict shape")
        print("Sample:", {k: detail[k] for k in ("lesson_id", "completion_percent", "is_completed", "lesson_type")})

        await db.rollback()

    print("All lesson completion checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
