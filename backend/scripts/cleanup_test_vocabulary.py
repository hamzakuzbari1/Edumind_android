"""Find (and optionally remove) "_test"-suffixed rows that leaked into live vocabulary data.

Covers both places a student-facing vocabulary word can live:
  - language_content_items (content_type='vocabulary') — flashcard deck words (AI daily batch + bank)
  - language_vocabulary_word_bank — the fixed per-level word bank (Phase 7; formerly the never-
    populated offline "catalog" table this script originally targeted)

Safety:
- Default mode is dry-run: prints every matching row, writes nothing.
- Pass --apply to actually delete the matched rows.
- Matches word ILIKE '%_test%' (covers "resilience_test_zz", "foo_test", etc.) — review the
  dry-run output before applying, since this is a substring match.

Usage (from backend/):
    python scripts/cleanup_test_vocabulary.py            # dry run
    python scripts/cleanup_test_vocabulary.py --apply    # actually delete
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import AsyncSessionLocal

_PATTERN = "%\\_test%"  # ESCAPE '\' below — matches a literal "_test" substring, not the SQL wildcard "_"


async def _find_content_item_rows(db):
    rows = await db.execute(
        text(
            """
            SELECT id, student_id, language_id, title, body_json->>'word' AS word,
                   body_json->>'source' AS source, created_at
            FROM language_content_items
            WHERE content_type = 'vocabulary'
              AND (body_json->>'word') ILIKE :pattern ESCAPE '\\'
            ORDER BY id
            """
        ),
        {"pattern": _PATTERN},
    )
    return rows.mappings().all()


async def _find_catalog_rows(db):
    rows = await db.execute(
        text(
            """
            SELECT id, word, cefr_level, topic, created_at
            FROM language_vocabulary_word_bank
            WHERE word ILIKE :pattern ESCAPE '\\'
            ORDER BY id
            """
        ),
        {"pattern": _PATTERN},
    )
    return rows.mappings().all()


async def run(apply: bool) -> int:
    async with AsyncSessionLocal() as db:
        content_rows = await _find_content_item_rows(db)
        catalog_rows = await _find_catalog_rows(db)

        print(f"language_content_items matches: {len(content_rows)}")
        for r in content_rows:
            print(f"  id={r['id']} word={r['word']!r} source={r['source']!r} "
                  f"student_id={r['student_id']} created_at={r['created_at']}")

        print(f"language_vocabulary_word_bank matches: {len(catalog_rows)}")
        for r in catalog_rows:
            print(f"  id={r['id']} word={r['word']!r} cefr_level={r['cefr_level']!r} "
                  f"topic={r['topic']!r} created_at={r['created_at']}")

        total = len(content_rows) + len(catalog_rows)
        if total == 0:
            print("\nNo _test-suffixed vocabulary rows found.")
            return 0

        if not apply:
            print(f"\nDRY RUN — {total} row(s) would be deleted. Re-run with --apply to delete them.")
            return 0

        content_ids = [r["id"] for r in content_rows]
        catalog_ids = [r["id"] for r in catalog_rows]
        if content_ids:
            await db.execute(
                text("DELETE FROM language_content_items WHERE id = ANY(:ids)"),
                {"ids": content_ids},
            )
        if catalog_ids:
            await db.execute(
                text("DELETE FROM language_vocabulary_word_bank WHERE id = ANY(:ids)"),
                {"ids": catalog_ids},
            )
        await db.commit()
        print(f"\nDeleted {total} row(s).")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Find/remove _test-suffixed vocabulary rows")
    parser.add_argument("--apply", action="store_true", help="Actually delete matches (default: dry run)")
    args = parser.parse_args()
    return asyncio.run(run(apply=args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
