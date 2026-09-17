"""CLI entry point: seed and MVP-activate speaking-placement prompts (Blueprint Phase A0+A1, MVP
activation).

MVP product decision: these 30 items are used for MVP placement WITHOUT a completed human-review
pass. This script never claims a human review was performed -- see the service module's
MVP_REVIEW_STATUS marker, stamped into every item's body_json.

The actual seed content and idempotent insert/update/activation logic live in
app/services/language_speaking_placement_seed_service.py (kept importable/testable there,
since backend/scripts/ is excluded from the test Docker image). This file is just the
command-line wrapper: argument parsing, opening a session, printing a summary.

Safety:
- Default mode is dry-run. Nothing is written unless --apply is passed.
- Requires the 0003_placement_qbank migration/table to exist.
- --apply both syncs content (never touching is_verified/is_active on an existing row) and runs
  the one-time MVP activation pass (only touches rows still in the pristine, never-touched
  draft state) -- see the service module's docstring for the exact idempotency/re-run guarantees.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import AsyncSessionLocal
from app.services.language_speaking_placement_seed_service import (
    SPEAKING_PROMPT_SEEDS,
    _language_id,
    _table_exists,
    activate_mvp_drafts,
    seed_speaking_prompts,
    summarize,
)


async def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Seed and MVP-activate speaking placement prompts. Never claims a human review was "
            "performed -- items are explicitly marked mvp_approved_pending_full_review."
        )
    )
    parser.add_argument("--language-code", default="en")
    parser.add_argument("--apply", action="store_true", help="Write changes. Default is dry-run.")
    args = parser.parse_args()

    async with AsyncSessionLocal() as db:
        if not await _table_exists(db):
            print("Question-bank table is missing. Run Alembic migration 0003_placement_qbank first.")
            return 1

        language_id = await _language_id(db, args.language_code)
        if language_id is None:
            print(f"Active language {args.language_code!r} not found.")
            return 1

        inserts, updates = await seed_speaking_prompts(
            db, language_id=language_id, language_code=args.language_code, apply=args.apply
        )
        activated = 0
        if args.apply:
            activated = await activate_mvp_drafts(db, language_code=args.language_code)

        mode = "APPLY" if args.apply else "DRY-RUN"
        print(f"{mode}: seeds={len(SPEAKING_PROMPT_SEEDS)} inserts={inserts} updates={updates} activated={activated}")
        print(summarize(SPEAKING_PROMPT_SEEDS))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
