"""Import a vocabulary word-bank + content-items export (see export_vocabulary_data.py)
into this machine's database — no Claude/Gemini calls, no API spend, just loading data
that was already generated and paid for once.

Idempotent and safe to re-run: word-bank rows are inserted with ON CONFLICT DO NOTHING on
(word, cefr_level); content items are skipped if a matching (language, level, word) row
already exists on this machine, rather than trusting the exported id/language_id (which
belong to the machine that produced the export, not necessarily this one).

Dry-run by default — prints what would be imported. Pass --apply to actually write.

Usage (from backend/):
    python scripts/import_vocabulary_data.py                # dry run
    python scripts/import_vocabulary_data.py --apply         # actually import
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import AsyncSessionLocal
from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.vocabulary_word_bank import LanguageVocabularyWordBank
from app.services.language_content_service import normalize_word
from app.services.language_subscription_service import get_default_language

_IN_DIR = Path(__file__).resolve().parents[1] / "db_exports"


def _level_value(level: LanguageLevel | str | None) -> str | None:
    if isinstance(level, LanguageLevel):
        return level.value
    return str(level) if level is not None else None


async def import_word_bank(db, *, apply: bool) -> dict:
    path = _IN_DIR / "language_vocabulary_word_bank.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    existing = {
        (w, lvl) for w, lvl in (
            await db.execute(select(LanguageVocabularyWordBank.word, LanguageVocabularyWordBank.cefr_level))
        ).all()
    }
    to_insert = []
    for r in rows:
        level = LanguageLevel(r["cefr_level"])
        if (r["word"], level) in existing:
            continue
        to_insert.append({**r, "cefr_level": level})

    if not apply:
        return {"file": path.name, "total_in_file": len(rows), "already_present": len(rows) - len(to_insert), "would_insert": len(to_insert)}

    inserted = 0
    if to_insert:
        stmt = pg_insert(LanguageVocabularyWordBank).values(to_insert).on_conflict_do_nothing(
            index_elements=["word", "cefr_level"]
        )
        result = await db.execute(stmt)
        inserted = result.rowcount or 0
        await db.commit()
    return {"file": path.name, "total_in_file": len(rows), "already_present": len(rows) - len(to_insert), "inserted": inserted}


async def import_content_items(db, *, apply: bool) -> dict:
    path = _IN_DIR / "language_content_items_vocabulary.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    language = await get_default_language(db)

    existing_items = {
        (normalize_word((item.body_json or {}).get("word") or ""), _level_value(item.level)): item
        for item in (
            await db.execute(
                select(LanguageContentItem).where(
                    LanguageContentItem.language_id == language.id,
                    LanguageContentItem.content_type == "vocabulary",
                )
            )
        ).scalars().all()
    }

    to_insert = []
    image_url_backfilled = 0
    for r in rows:
        exported_body = r.get("body_json") or {}
        word = normalize_word(exported_body.get("word") or "")
        level = LanguageLevel(r["level"]) if r.get("level") else None
        item_key = (word, _level_value(level))
        existing_item = existing_items.get(item_key)
        if not word:
            continue
        if existing_item is not None:
            existing_body = dict(existing_item.body_json or {})
            exported_image_url = str(exported_body.get("image_url") or "").strip()
            if exported_image_url and not str(existing_body.get("image_url") or "").strip():
                existing_body["image_url"] = exported_image_url
                if exported_body.get("image_prompt") and not existing_body.get("image_prompt"):
                    existing_body["image_prompt"] = exported_body.get("image_prompt")
                existing_item.body_json = existing_body
                image_url_backfilled += 1
            continue
        existing_items[item_key] = None
        to_insert.append(
            LanguageContentItem(
                language_id=language.id,
                student_id=None,
                skill=LanguageSkill(r["skill"]) if r.get("skill") else LanguageSkill.reading,
                level=level,
                content_type=r["content_type"],
                title=r.get("title") or word,
                body_json=r.get("body_json") or {},
                is_published=bool(r.get("is_published", True)),
                sort_order=int(r.get("sort_order") or 0),
            )
        )

    if not apply:
        return {
            "file": path.name,
            "total_in_file": len(rows),
            "already_present": len(rows) - len(to_insert),
            "would_insert": len(to_insert),
            "would_backfill_image_url": image_url_backfilled,
        }

    if to_insert:
        db.add_all(to_insert)
    if to_insert or image_url_backfilled:
        await db.commit()
    return {
        "file": path.name,
        "total_in_file": len(rows),
        "already_present": len(rows) - len(to_insert),
        "inserted": len(to_insert),
        "image_url_backfilled": image_url_backfilled,
    }


async def run(*, apply: bool) -> int:
    async with AsyncSessionLocal() as db:
        bank_summary = await import_word_bank(db, apply=apply)
        content_summary = await import_content_items(db, apply=apply)

    print("word bank:", bank_summary)
    print("content items:", content_summary)
    if not apply:
        print("\nDRY RUN — no rows written. Re-run with --apply to import.")
        print("Reminder: this only loads database rows. Image FILES referenced by content")
        print("items' body_json.image_url still need to be copied into")
        print("backend/uploads/vocabulary_images/ separately (not part of this import).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Import exported vocabulary word bank + content items")
    parser.add_argument("--apply", action="store_true", help="Actually write rows (default: dry run)")
    args = parser.parse_args()
    return asyncio.run(run(apply=args.apply))


if __name__ == "__main__":
    sys.exit(main())
