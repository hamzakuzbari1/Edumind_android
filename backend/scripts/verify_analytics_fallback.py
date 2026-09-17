"""Verify analytics content-level fallback for C1+ students."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import AsyncSessionLocal
from app.services.language_analytics_service import build_skill_growth_snapshot
from app.models.language.analytics import LanguageAnalytics
from sqlalchemy import select


async def main(student_id: int = 5) -> None:
    async with AsyncSessionLocal() as db:
        from app.models.language.catalog import Language

        lang = (await db.execute(select(Language).where(Language.code == "en"))).scalar_one()
        a = (
            await db.execute(
                select(LanguageAnalytics).where(
                    LanguageAnalytics.student_id == student_id,
                    LanguageAnalytics.language_id == lang.id,
                )
            )
        ).scalar_one_or_none()
        snap = await build_skill_growth_snapshot(db, student_id=student_id, language_id=lang.id, analytics=a)
        print(f"student_id={student_id}")
        print(f"reading content_level={snap['reading'].get('content_level')} total={snap['reading']['lessons_total']}")
        print(f"vocab content_level={snap['vocabulary'].get('content_level')} total={snap['vocabulary']['total_words']}")
        assert snap["reading"]["lessons_total"] > 0, "C1 student should get B1 reading fallback"
        assert snap["vocabulary"]["total_words"] > 0, "C1 student should get B1 vocab fallback"
        print("PASS")


if __name__ == "__main__":
    asyncio.run(main())
