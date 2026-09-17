"""CLI entry point: Reading MVP v1 draft-to-bank insertion -- dry-run + apply + cutover.

Parses and validates backend/content_drafts/reading_mvp_v1_draft.md and either reports what would
be inserted into LanguagePlacementQuestionBankItem (default, dry-run) or actually performs that
idempotent insert/update (--apply). Every fresh insert lands is_active=False, is_verified=False.
Use --activate-cutover for the deliberate production cutover: activate the 60 MVP rows and
soft-retire old active Reading content_seed rows.

The actual parse/validate/apply logic lives in
app/services/language_reading_bank_seed_service.py (kept importable/testable there, since
backend/scripts/ is excluded from the test Docker image). This file is just the command-line
wrapper: argument parsing, opening a session when --apply is used, and printing a summary.

Usage (from backend/):
    python scripts/seed_reading_bank_mvp_v1.py                     # dry-run (default)
    python scripts/seed_reading_bank_mvp_v1.py --apply             # insert/update, inactive/unverified
    python scripts/seed_reading_bank_mvp_v1.py --activate-cutover  # activate MVP + retire old Reading bank
    python scripts/seed_reading_bank_mvp_v1.py --apply --language-code en
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_reading_bank_seed_service import (
    activate_reading_mvp_v1_cutover,
    apply_seed_batch,
    build_dry_run_summary,
    seed_reading_boundary_v1,
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
            print(f"  [{issue.draft_id or '-'}] {issue.field}: {issue.message}")
    if summary.warnings:
        print("\nWARNINGS (non-blocking):")
        for issue in summary.warnings:
            print(f"  [{issue.draft_id or '-'}] {issue.field}: {issue.message}")


async def _run_apply(language_code: str) -> int:
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        summary, result = await apply_seed_batch(db, language_code=language_code, apply=True)

    _print_summary(summary)
    if not summary.is_valid:
        print("\nFAILED: validation errors, nothing was written.")
        return 1
    if result is None:
        print("\nFAILED: apply did not run (see errors above, e.g. unresolved language code).")
        return 1
    print(f"\nAPPLY OK: inserted={result.inserted} updated={result.updated} (all rows inactive/unverified).")
    return 0


async def _run_cutover(language_code: str) -> int:
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        summary, result = await activate_reading_mvp_v1_cutover(db, language_code=language_code)

    _print_summary(summary)
    if not summary.is_valid:
        print("\nFAILED: validation/cutover errors, database cutover did not complete.")
        return 1
    if result is None:
        print("\nFAILED: cutover did not run (see errors above).")
        return 1
    print(
        "\nCUTOVER OK: "
        f"inserted={result.inserted} updated={result.updated} "
        f"activated_mvp_rows={result.activated_mvp_rows} "
        f"retired_content_seed_rows={result.retired_content_seed_rows} "
        f"active_mvp_rows={result.active_mvp_rows} "
        f"active_content_seed_rows={result.active_content_seed_rows} "
        f"boundary_inserted={result.boundary_inserted} "
        f"boundary_updated={result.boundary_updated} "
        f"boundary_activated_rows={result.boundary_activated_rows} "
        f"active_boundary_rows={result.active_boundary_rows}."
    )
    return 0


async def _run_boundaries(language_code: str) -> int:
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await seed_reading_boundary_v1(db, language_code=language_code, activate=True)

    if result is None:
        print(f"FAILED: language code {language_code!r} not found or inactive.")
        return 1
    print(
        "BOUNDARY SEED OK: "
        f"inserted={result.inserted} updated={result.updated} "
        f"activated_rows={result.activated_rows} "
        f"active_boundary_rows={result.active_boundary_rows}."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Parse, validate, and (with --apply) idempotently insert/update the Reading MVP v1 "
            "60-item draft bank. Default is dry-run -- nothing is written unless --apply is passed."
        )
    )
    parser.add_argument("--apply", action="store_true", help="Write to the database. Default is dry-run.")
    parser.add_argument(
        "--activate-cutover",
        action="store_true",
        help="Insert/update the 60 MVP rows, mark them active+verified, and soft-retire old active Reading content_seed rows.",
    )
    parser.add_argument(
        "--activate-boundaries",
        action="store_true",
        help="Insert/update and activate the Reading boundary-confirmation rows only.",
    )
    parser.add_argument("--language-code", default="en", help="Language code to attach new rows to (default: en).")
    args = parser.parse_args()

    if args.activate_cutover:
        return asyncio.run(_run_cutover(args.language_code))

    if args.activate_boundaries:
        return asyncio.run(_run_boundaries(args.language_code))

    if args.apply:
        return asyncio.run(_run_apply(args.language_code))

    summary = build_dry_run_summary()
    print("DRY-RUN:")
    _print_summary(summary)
    if summary.is_valid:
        print("\nOK: draft is valid. No database writes were made (pass --apply to write).")
    else:
        print("\nFAILED: draft has validation errors. No database writes were made.")
    return 0 if summary.is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
