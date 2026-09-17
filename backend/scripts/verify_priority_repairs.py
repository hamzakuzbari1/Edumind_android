"""Verify priority repairs: DB, planner API, parent notes routes."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from httpx import ASGITransport
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.core.test_users import TEST_USER_PASSWORD, default_test_email
from app.main import app


def check_db_columns() -> bool:
    engine = create_engine(get_settings().DATABASE_URL.replace("+asyncpg", ""))
    with engine.connect() as conn:
        cols = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'student_profiles'"
                )
            ).fetchall()
        }
    ok = "hobbies_json" in cols
    print(f"[DB] hobbies_json present: {'PASS' if ok else 'FAIL'}")
    return ok


def check_routes() -> bool:
    paths = {getattr(r, "path", "") for r in app.routes}
    planner = [p for p in paths if p.startswith("/api/student/planner")]
    parent_notes = [p for p in paths if "/parent/notes" in p]
    print(f"[Routes] student planner: {len(planner)} endpoints")
    for p in sorted(planner):
        print(f"  {p}")
    print(f"[Routes] parent notes: {len(parent_notes)} endpoints")
    ok = len(planner) >= 3 and len(parent_notes) >= 1
    print(f"[Routes] planner wired: {'PASS' if ok else 'FAIL'}")
    return ok


async def check_authenticated_planner() -> bool:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
        r = await client.post(
            "/api/auth/login",
            json={"email": default_test_email("auth_student"), "password": TEST_USER_PASSWORD},
        )
        if r.status_code != 200:
            print(f"[Auth] login FAILED {r.status_code}: {r.text[:200]}")
            return False
        print("[Auth] login PASS")
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        checks = [
            ("GET", "/api/student/planner"),
            ("GET", "/api/student/planner/summary"),
            ("POST", "/api/student/planner/generate"),
        ]
        all_ok = True
        for method, path in checks:
            if method == "GET":
                resp = await client.get(path, headers=headers)
            else:
                resp = await client.post(path, headers=headers, json={})
            ok = resp.status_code == 200
            all_ok = all_ok and ok
            label = "PASS" if ok else "FAIL"
            print(f"[Planner] {method} {path} -> {resp.status_code} {label}")
            if ok and path.endswith("/planner"):
                data = resp.json()
                print(
                    f"  schedule={len(data.get('schedule', []))} "
                    f"weekly_plan={len(data.get('weekly_plan', []))} "
                    f"analytics={len(data.get('subject_analytics', []))}"
                )
        return all_ok


async def check_parent_notes_auth() -> bool:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30) as client:
        r = await client.post(
            "/api/auth/login",
            json={"email": default_test_email("auth_parent"), "password": TEST_USER_PASSWORD},
        )
        if r.status_code != 200:
            print(f"[Parent auth] login FAILED {r.status_code}")
            return False
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        resp = await client.get("/api/parent/notes", headers=headers)
        ok = resp.status_code == 200
        print(f"[Parent notes] GET /api/parent/notes -> {resp.status_code} {'PASS' if ok else 'FAIL'}")
        return ok


async def main() -> int:
    print("=== Priority Repair Verification (EduSpark-Syrian) ===\n")
    results = [
        check_db_columns(),
        check_routes(),
        await check_authenticated_planner(),
        await check_parent_notes_auth(),
    ]
    passed = sum(results)
    print(f"\n=== {passed}/{len(results)} checks passed ===")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
