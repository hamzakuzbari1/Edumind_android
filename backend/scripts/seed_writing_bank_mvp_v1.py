"""CLI entry point: Writing MVP v1 draft-to-bank insertion, dry-run, and cutover.

Usage (from backend/):
    python scripts/seed_writing_bank_mvp_v1.py                     # dry-run
    python scripts/seed_writing_bank_mvp_v1.py --apply             # insert/update inactive
    python scripts/seed_writing_bank_mvp_v1.py --activate-cutover  # activate MVP + retire old Writing bank
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_writing_bank_seed_service import (
    activate_writing_mvp_v1_cutover,
    apply_seed_batch,
    build_dry_run_summary,
)


def _print_summary(summary) -> None:
    print(f"parsed={summary.total_parsed} candidates={len(summary.candidates)}")
    print(f"  errors={len(summary.errors)} warnings={len(summary.warnings)}")
    print("  distribution:")
    for level, count in sorted(summary.distribution.items()):
        print(f"    {level}: {count}")
    if summary.errors:
        print("\nVALIDATION ERRORS:")
        for issue in summary.errors:
            print(f"  [{issue.stable_key or '-'}] {issue.field}: {issue.message}")
    if summary.warnings:
        print("\nWARNINGS:")
        for issue in summary.warnings:
            print(f"  [{issue.stable_key or '-'}] {issue.field}: {issue.message}")


async def _run_apply(language_code: str) -> int:
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        summary, result = await apply_seed_batch(db, language_code=language_code, apply=True)

    _print_summary(summary)
    if not summary.is_valid or result is None:
        print("\nFAILED: validation errors, nothing was written.")
        return 1
    print(f"\nAPPLY OK: inserted={result.inserted} updated={result.updated} (all rows inactive/unverified).")
    return 0


async def _run_cutover(language_code: str) -> int:
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        summary, result = await activate_writing_mvp_v1_cutover(db, language_code=language_code)

    _print_summary(summary)
    if not summary.is_valid or result is None:
        print("\nFAILED: validation/cutover errors, database cutover did not complete.")
        return 1
    print(
        "\nCUTOVER OK: "
        f"inserted={result.inserted} updated={result.updated} "
        f"activated_mvp_rows={result.activated_mvp_rows} "
        f"retired_content_seed_rows={result.retired_content_seed_rows} "
        f"active_mvp_rows={result.active_mvp_rows} "
        f"active_content_seed_rows={result.active_content_seed_rows}."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse, validate, and seed the Writing MVP v1 60-prompt placement bank."
    )
    parser.add_argument("--apply", action="store_true", help="Write to the database. Default is dry-run.")
    parser.add_argument(
        "--activate-cutover",
        action="store_true",
        help="Insert/update the 60 MVP rows, mark them active+verified, and soft-retire old active Writing content_seed rows.",
    )
    parser.add_argument("--language-code", default="en", help="Language code to attach new rows to (default: en).")
    args = parser.parse_args()

    if args.activate_cutover:
        return asyncio.run(_run_cutover(args.language_code))
    if args.apply:
        return asyncio.run(_run_apply(args.language_code))

    summary = build_dry_run_summary()
    print("DRY-RUN:")
    _print_summary(summary)
    if summary.is_valid:
        print("\nOK: draft is valid. No database writes were made.")
    else:
        print("\nFAILED: draft has validation errors. No database writes were made.")
    return 0 if summary.is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
