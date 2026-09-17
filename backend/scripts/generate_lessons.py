"""Nightly AI lesson generation job.

Run off-peak (cron / Task Scheduler):
    cd backend && python scripts/generate_lessons.py [target_per_bucket]

Tops every (skill, level) lesson pool up to the target count using Gemini, validates, and
stores the new lessons as published content. Safe no-op when GEMINI_API_KEY is unset.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import get_db
from app.services.language_lesson_generation_service import TARGET_PER_BUCKET, run_nightly_topup


async def main(target: int) -> int:
    async for db in get_db():
        summary = await run_nightly_topup(db, target=target)
        await db.commit()
        print("nightly lesson generation:", summary)
        return 0
    return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tgt = int(sys.argv[1]) if len(sys.argv) > 1 else TARGET_PER_BUCKET
    sys.exit(asyncio.run(main(tgt)))
