"""CLI entry point: bundled Listening draft-to-bank insertion (Phase 6C dry-run + apply
implementation for a later phase).

Parses and validates backend/content_drafts/listening_bundles_v1_draft.md and either reports what
would be inserted into LanguagePlacementQuestionBankItem (default, dry-run) or actually performs
that idempotent insert/update (--apply). Every fresh insert lands is_active=False,
is_verified=False -- activation is a deliberate, separate, later step this script never performs.

The actual parse/validate/apply logic lives in
app/services/language_listening_bundle_seed_service.py (kept importable/testable there, since
backend/scripts/ is excluded from the test Docker image). This file is just the command-line
wrapper: argument parsing, opening a session when --apply is used, and printing a summary.

Usage (from backend/):
    python scripts/seed_listening_bundles.py                     # dry-run (default)
    python scripts/seed_listening_bundles.py --apply             # insert/update, inactive/unverified
    python scripts/seed_listening_bundles.py --apply --language-code en
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_listening_bundle_seed_service import apply_seed_batch, build_dry_run_summary


def _print_summary(summary) -> None:
    mcq_total = sum(v for (_lvl, qt), v in summary.distribution.items() if qt == "mcq")
    gap_fill_total = sum(v for (_lvl, qt), v in summary.distribution.items() if qt == "gap_fill")
    print(f"parsed={summary.total_parsed} candidates={len(summary.candidates)}")
    print(f"  errors={len(summary.errors)} warnings={len(summary.warnings)}")
    print(f"  mcq_bundles={mcq_total} gap_fill_bundles={gap_fill_total} answer_points={summary.answer_points}")
    print("  distribution:")
    for (level, qtype), count in sorted(summary.distribution.items()):
        print(f"    {level} {qtype}: {count}")
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Parse, validate, and (with --apply) idempotently insert/update the bundled Listening "
            "30-item draft bank. Default is dry-run -- nothing is written unless --apply is passed."
        )
    )
    parser.add_argument("--apply", action="store_true", help="Write to the database. Default is dry-run.")
    parser.add_argument("--language-code", default="en", help="Language code to attach new rows to (default: en).")
    args = parser.parse_args()

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
