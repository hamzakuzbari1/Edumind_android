"""Export the fixed vocabulary word bank + already-illustrated content items to portable
JSON, so a teammate can load the exact same data on their own machine without re-spending
Claude/Gemini API credits regenerating it.

Writes two files under backend/db_exports/:
  - language_vocabulary_word_bank.json  (all 1350 word-bank rows)
  - language_content_items_vocabulary.json  (every vocabulary content item — the shared,
    already-enriched/illustrated cards students have actually reached)

Pair with import_vocabulary_data.py on the receiving machine. Image FILES referenced by
content items (body_json.image_url) are NOT included here — they live under
backend/uploads/vocabulary_images/ and must be transferred separately (see
VOCABULARY_STATUS.md / the export instructions printed at the end of this script).

Usage (from backend/):
    python scripts/export_vocabulary_data.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.language.content import LanguageContentItem
from app.models.language.vocabulary_word_bank import LanguageVocabularyWordBank

_OUT_DIR = Path(__file__).resolve().parents[1] / "db_exports"


def _word_bank_row_to_dict(row: LanguageVocabularyWordBank) -> dict:
    return {
        "cefr_level": row.cefr_level.value,
        "word": row.word,
        "part_of_speech": row.part_of_speech,
        "translation_ar": row.translation_ar,
        "definition": row.definition,
        "example_sentence": row.example_sentence,
        "example_sentence_ar": row.example_sentence_ar,
        "image_prompt": row.image_prompt,
        "topic": row.topic,
        "sort_order": row.sort_order,
    }


def _content_item_row_to_dict(row: LanguageContentItem) -> dict:
    return {
        "language_id": row.language_id,
        "skill": row.skill.value if row.skill else None,
        "level": row.level.value if row.level else None,
        "content_type": row.content_type,
        "title": row.title,
        "body_json": row.body_json,
        "is_published": row.is_published,
        "sort_order": row.sort_order,
    }


async def run() -> int:
    _OUT_DIR.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as db:
        bank_rows = (
            await db.execute(select(LanguageVocabularyWordBank).order_by(LanguageVocabularyWordBank.id))
        ).scalars().all()
        content_rows = (
            await db.execute(
                select(LanguageContentItem)
                .where(LanguageContentItem.content_type == "vocabulary")
                .order_by(LanguageContentItem.id)
            )
        ).scalars().all()

    bank_out = [_word_bank_row_to_dict(r) for r in bank_rows]
    content_out = [_content_item_row_to_dict(r) for r in content_rows]

    bank_path = _OUT_DIR / "language_vocabulary_word_bank.json"
    content_path = _OUT_DIR / "language_content_items_vocabulary.json"
    bank_path.write_text(json.dumps(bank_out, indent=2, ensure_ascii=False), encoding="utf-8")
    content_path.write_text(json.dumps(content_out, indent=2, ensure_ascii=False), encoding="utf-8")

    image_urls = [
        (r.body_json or {}).get("image_url") for r in content_rows if (r.body_json or {}).get("image_url")
    ]

    print(f"Wrote {len(bank_out)} word-bank rows -> {bank_path}")
    print(f"Wrote {len(content_out)} vocabulary content items -> {content_path}")
    print(f"{len(image_urls)} of those reference an image file under backend/uploads/ "
          "— transfer that folder separately (see instructions).")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
