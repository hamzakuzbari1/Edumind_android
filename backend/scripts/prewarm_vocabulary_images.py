"""Vocabulary image prewarm — nightly background job.

Predicts which words active students will likely reach in their level's word bank over
the next ~1-2 days and pre-generates + caches their images, so the lazy fallback
(get_or_create_word_image, unchanged) rarely has to generate one on the spot in front of
a student. Purely additive — safe to skip a night or re-run; once an image is generated
it's cached forever on the shared content item regardless of whether this job ever runs.

Run off-peak (cron / Task Scheduler):
    cd backend && python scripts/prewarm_vocabulary_images.py [lookahead]
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import get_db
from app.services.language_vocabulary_prewarm_service import LOOKAHEAD_WORDS, run_nightly_image_prewarm


async def main(lookahead: int) -> int:
    async for db in get_db():
        summary = await run_nightly_image_prewarm(db, lookahead=lookahead)
        print("vocabulary image prewarm:", summary)
        return 0
    return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    la = int(sys.argv[1]) if len(sys.argv) > 1 else LOOKAHEAD_WORDS
    sys.exit(asyncio.run(main(la)))
