"""One-shot backfill: language_analytics → language_progression (Phase 4.2.1).

Usage (from backend/):
    python scripts/backfill_language_progression.py
    python scripts/backfill_language_progression.py --batch-size 100
    python scripts/backfill_language_progression.py --dry-run

Idempotent, batched, resumable (skips rows already present unless --force-update).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401 — register all ORM mappers before queries
from app.models.user import User  # noqa: F401

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.language.analytics import LanguageAnalytics
from app.models.language.progression import LanguageProgression
from app.services.language_progression_service import (
    backfill_from_analytics_row,
    official_levels_from_analytics,
)


async def run_backfill(
    *,
    batch_size: int = 100,
    dry_run: bool = False,
    force_update: bool = False,
) -> dict[str, int]:
    stats = {
        "analytics_total": 0,
        "already_present": 0,
        "inserted": 0,
        "updated": 0,
    }

    async with AsyncSessionLocal() as db:
        last_student_id = 0
        last_language_id = 0

        while True:
            q = (
                select(LanguageAnalytics)
                .where(
                    (LanguageAnalytics.student_id > last_student_id)
                    | (
                        (LanguageAnalytics.student_id == last_student_id)
                        & (LanguageAnalytics.language_id > last_language_id)
                    )
                )
                .order_by(LanguageAnalytics.student_id, LanguageAnalytics.language_id)
                .limit(batch_size)
            )
            batch = (await db.execute(q)).scalars().all()
            if not batch:
                break

            for analytics in batch:
                stats["analytics_total"] += 1
                last_student_id = analytics.student_id
                last_language_id = analytics.language_id

                existing = await db.get(
                    LanguageProgression,
                    {"student_id": analytics.student_id, "language_id": analytics.language_id},
                )
                if existing is not None and not force_update:
                    stats["already_present"] += 1
                    continue

                if dry_run:
                    levels = official_levels_from_analytics(analytics)
                    if existing is None:
                        stats["inserted"] += 1
                    else:
                        stats["updated"] += 1
                    continue

                before = existing is not None
                await backfill_from_analytics_row(db, analytics, force=True)
                if before:
                    stats["updated"] += 1
                else:
                    stats["inserted"] += 1

            if not dry_run:
                await db.commit()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill language_progression from analytics")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--force-update",
        action="store_true",
        help="Re-apply backfill even when a progression row already exists",
    )
    args = parser.parse_args()

    stats = asyncio.run(
        run_backfill(
            batch_size=max(1, args.batch_size),
            dry_run=args.dry_run,
            force_update=args.force_update,
        )
    )
    print("backfill_language_progression:", stats)


if __name__ == "__main__":
    main()
