"""CLI entry point: backfill persistent Supertonic audio for reachable Listening bank items.

The actual scan/synthesis/idempotency logic lives in
app/services/language_listening_bank_audio_backfill_service.py (kept importable/testable there,
since backend/scripts/ is excluded from the test Docker image). This file is just the
command-line wrapper: argument parsing, opening a session, printing a summary.

Usage (from backend/, or via `docker compose exec backend python scripts/backfill_listening_bank_audio.py`):
    python scripts/backfill_listening_bank_audio.py                # dry-run, all reachable rows
    python scripts/backfill_listening_bank_audio.py --apply        # actually synthesize + persist
    python scripts/backfill_listening_bank_audio.py --apply --force            # regenerate everything
    python scripts/backfill_listening_bank_audio.py --apply --item-id 23      # target one row

    # Scoped targeting for a not-yet-active draft batch (e.g. the listening_mvp_60 rows, which are
    # intentionally is_active=False/is_verified=False until a separate, later activation step):
    python scripts/backfill_listening_bank_audio.py --stable-key-prefix "listening_mvp_60:" --source listening_mvp_60_draft
    python scripts/backfill_listening_bank_audio.py --stable-key-prefix "listening_mvp_60:" --source listening_mvp_60_draft --apply

Safety:
- Default mode is dry-run. Nothing is written (no synthesis, no DB writes) unless --apply is passed.
- Never runs automatically -- there is no server-startup hook for this script.
- Default scope (no --stable-key-prefix/--source) only ever touches skill="listening",
  is_active=True, is_verified=True bank rows with a resolvable transcript. Rows without one (the
  known incomplete scaffold rows referencing /language-assets/en/lessons/listening/, which have
  neither a real audio file nor a transcript) are reported as "no_transcript" and left completely
  untouched.
- --stable-key-prefix and/or --source narrow the query to that prefix/source and, only for that
  narrowed scope, also include inactive/unverified rows -- there is no way to broadly include every
  inactive/unverified listening row without one of these explicit narrowing flags.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import AsyncSessionLocal
from app.services.language_listening_bank_audio_backfill_service import run_backfill


async def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill persistent Supertonic audio for reachable Listening placement bank items, "
            "writing audio_meta_json so the live exam prefers cached audio over runtime synthesis."
        )
    )
    parser.add_argument("--language-code", default="en")
    parser.add_argument("--apply", action="store_true", help="Write changes. Default is dry-run.")
    parser.add_argument(
        "--force",
        "--regenerate",
        dest="force",
        action="store_true",
        help="Regenerate even if the cached audio already looks valid (metadata + file both present).",
    )
    parser.add_argument(
        "--item-id",
        type=int,
        default=None,
        help="Only process this single bank item ID (must still satisfy the rest of the scope).",
    )
    parser.add_argument(
        "--stable-key-prefix",
        default=None,
        help=(
            "Narrow to rows whose stable_key starts with this exact prefix (e.g. 'listening_mvp_60:'). "
            "Also lifts the is_active/is_verified requirement for this narrowed scope only."
        ),
    )
    parser.add_argument(
        "--source",
        default=None,
        help=(
            "Narrow to rows with this exact source column value (e.g. 'listening_mvp_60_draft'). "
            "Can be combined with --stable-key-prefix for extra safety; also lifts is_active/"
            "is_verified for this narrowed scope only."
        ),
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help=(
            "Explicit acknowledgement that inactive/unverified rows may be included. Only valid "
            "together with --stable-key-prefix and/or --source -- rejected on its own."
        ),
    )
    args = parser.parse_args()

    async with AsyncSessionLocal() as db:
        try:
            summary = await run_backfill(
                db,
                language_code=args.language_code,
                apply=args.apply,
                force=args.force,
                item_id=args.item_id,
                stable_key_prefix=args.stable_key_prefix,
                source=args.source,
                include_inactive=args.include_inactive,
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    mode = "APPLY" if args.apply else "DRY-RUN"
    scope = []
    if args.stable_key_prefix:
        scope.append(f"stable_key_prefix={args.stable_key_prefix!r}")
    if args.source:
        scope.append(f"source={args.source!r}")
    scope_str = f" scope=({', '.join(scope)})" if scope else ""
    print(
        f"{mode}{scope_str}: total={len(summary.results)} "
        f"synthesized={len(summary.synthesized)} "
        f"skipped={len(summary.skipped)} "
        f"would_synthesize={len(summary.would_synthesize)} "
        f"failed={len(summary.failed)} "
        f"no_transcript={len(summary.no_transcript)} "
        f"invalid_body_json={len(summary.invalid_body_json)}"
    )
    print(f"  by_question_type: {summary.by_question_type}")
    print(f"  by_level: {summary.by_level}")
    for r in summary.results:
        detail = f" ({r.reason})" if r.reason else ""
        extra = f" -> {r.public_url}" if r.public_url else ""
        print(f"  [{r.status}] bank_item_id={r.bank_item_id} level={r.level} question_type={r.question_type}{detail}{extra}")

    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
