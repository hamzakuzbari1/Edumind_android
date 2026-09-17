"""Audit listening lesson audio URLs vs files on disk. No placeholder generation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.core.config import get_settings


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    public = root / "public"
    engine = create_engine(get_settings().DATABASE_URL.replace("+asyncpg", ""))

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id, title, body_json->>'audio_url' AS audio_url "
                "FROM language_content_items "
                "WHERE skill = 'listening' AND is_published = true "
                "ORDER BY id"
            )
        ).fetchall()

    print("=== Listening Assets Audit (EduSpark-Syrian) ===\n")
    print(f"Published listening lessons in DB: {len(rows)}")
    print(f"Expected disk root: {public}\n")

    missing: list[tuple[int, str, str, Path]] = []
    present: list[tuple[int, str, Path]] = []
    bad_urls: list[tuple[int, str, str]] = []

    for item_id, title, url in rows:
        if not url or not str(url).strip():
            bad_urls.append((item_id, title or "", "(empty)"))
            continue
        url = str(url).strip()
        if url.startswith("/"):
            fp = public / url.lstrip("/")
        elif url.startswith("language-assets/"):
            fp = public / url
        else:
            bad_urls.append((item_id, title or "", url))
            continue
        if fp.is_file():
            present.append((item_id, url, fp))
        else:
            missing.append((item_id, title or "", url, fp))

    print(f"PRESENT on disk: {len(present)}")
    for item_id, url, fp in present[:5]:
        print(f"  id={item_id} {url} -> {fp.relative_to(root)}")
    if len(present) > 5:
        print(f"  ... and {len(present) - 5} more")

    print(f"\nMISSING on disk: {len(missing)}")
    for item_id, title, url, fp in missing:
        print(f"  id={item_id} | {title[:40]}")
        print(f"    DB URL:     {url}")
        print(f"    Expected:   {fp.relative_to(root)}")

    if bad_urls:
        print(f"\nINVALID/EMPTY URLs: {len(bad_urls)}")
        for item_id, title, url in bad_urls:
            print(f"  id={item_id} | {title[:40]} | url={url}")

    print("\n=== Summary ===")
    print(f"  Total lessons: {len(rows)}")
    print(f"  Files found:   {len(present)}")
    print(f"  Files missing: {len(missing)}")
    print(f"  Bad URLs:      {len(bad_urls)}")
    print("\nURLs use web path /language-assets/... served from public/language-assets/...")
    return 0 if not missing and not bad_urls else 1


if __name__ == "__main__":
    raise SystemExit(main())
