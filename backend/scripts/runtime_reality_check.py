"""Runtime reality check — planner, scenarios, parent notes, listening assets."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from app.core.config import get_settings


def check_db():
    print("\n=== DATABASE ===")
    e = create_engine(get_settings().DATABASE_URL.replace("+asyncpg", ""))
    with e.connect() as c:
        tables = [
            r[0]
            for r in c.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name LIKE '%scenario%'"
                )
            ).fetchall()
        ]
        print("scenario-related tables:", tables)
        if "language_conversation_scenarios" in tables:
            n = c.execute(text("SELECT COUNT(*) FROM language_conversation_scenarios")).scalar()
            print(f"language_conversation_scenarios rows: {n}")
        else:
            print("language_conversation_scenarios: MISSING")
        if "language_scenario_progress" in tables:
            n = c.execute(text("SELECT COUNT(*) FROM language_scenario_progress")).scalar()
            print(f"language_scenario_progress rows: {n}")
        # listening audio URLs
        rows = c.execute(
            text(
                "SELECT id, body_json->>'audio_url' AS url "
                "FROM language_content_items "
                "WHERE content_type='lesson' AND skill='listening' AND is_published=true "
                "LIMIT 10"
            )
        ).fetchall()
        print(f"listening lessons sampled: {len(rows)}")
        for rid, url in rows:
            exists = "MISSING" if not url else url
            print(f"  id={rid} url={exists}")


def check_routes():
    from app.main import app

    print("\n=== FASTAPI ROUTES ===")
    paths = sorted({getattr(r, "path", "") for r in app.routes})
    student_planner = [p for p in paths if p.startswith("/api/student/planner")]
    scenario = [p for p in paths if "scenario" in p.lower()]
    parent_notes = [p for p in paths if "/parent/notes" in p]
    print("student /planner routes:", student_planner or "NONE")
    print("scenario routes:", scenario or "NONE")
    print("parent notes routes:", len(parent_notes), "endpoints")


async def check_http():
    import httpx
    from app.main import app
    from httpx import ASGITransport

    print("\n=== HTTP (ASGI in-process) ===")
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        endpoints = [
            ("GET", "/api/student/planner"),
            ("GET", "/api/student/planner/summary"),
            ("POST", "/api/student/planner/generate"),
            ("GET", "/api/student/languages/speaking/scenarios"),
            ("POST", "/api/student/languages/speaking/scenarios/1/start"),
            ("GET", "/api/parent/notes"),
        ]
        for method, path in endpoints:
            try:
                if method == "GET":
                    r = await client.get(path)
                else:
                    r = await client.post(path, json={})
                print(f"{method} {path} -> {r.status_code}")
            except Exception as ex:
                print(f"{method} {path} -> ERROR {ex}")


def check_listening_files():
    print("\n=== LISTENING ASSET FILES ===")
    root = Path(__file__).resolve().parents[2]
    public = root / "public"
    lang_assets = public / "language-assets"
    print("public/language-assets exists:", lang_assets.is_dir())
    if lang_assets.is_dir():
        mp3s = list(lang_assets.rglob("*.mp3"))
        print("mp3 count under language-assets:", len(mp3s))
    e = create_engine(get_settings().DATABASE_URL.replace("+asyncpg", ""))
    with e.connect() as c:
        urls = [
            r[0]
            for r in c.execute(
                text(
                    "SELECT DISTINCT body_json->>'audio_url' FROM language_content_items "
                    "WHERE skill='listening' AND body_json->>'audio_url' IS NOT NULL LIMIT 20"
                )
            ).fetchall()
            if r[0]
        ]
    missing = 0
    for url in urls[:10]:
        if not url:
            continue
        rel = url.lstrip("/")
        fp = public / rel.replace("language-assets/", "language-assets/") if rel.startswith("language-assets") else public / rel
        # normalize: urls like /language-assets/foo.mp3
        if url.startswith("/"):
            fp = root / "public" / url.lstrip("/")
        else:
            fp = public / url
        ok = fp.is_file()
        if not ok:
            missing += 1
        print(f"  {url} -> {'EXISTS' if ok else '404 on disk'}")
    print(f"sampled missing files: {missing}/{min(10,len(urls))}")


def main():
    print("EduSpark-Syrian Runtime Reality Check")
    check_routes()
    check_db()
    check_listening_files()
    asyncio.run(check_http())


if __name__ == "__main__":
    main()
