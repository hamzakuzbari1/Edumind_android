"""Phase 8.2 runtime verification — grammar lessons routes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import httpx

BASE = "http://127.0.0.1:8000"
PASSWORD = "changeme"
REPORT: dict = {"phase": "8.2", "checks": []}


def record(name: str, ok: bool, **extra):
    REPORT["checks"].append({"name": name, "ok": ok, **extra})


def main() -> int:
    from app.main import app

    paths = [getattr(r, "path", "") for r in app.routes if "languages/lessons" in getattr(r, "path", "")]
    record("fastapi_lesson_routes", len(paths) >= 2, paths=paths)

    try:
        spec = httpx.get(f"{BASE}/openapi.json", timeout=10).json()
        lesson_paths = [p for p in spec.get("paths", {}) if "/languages/lessons" in p]
        record("live_openapi_lessons", len(lesson_paths) >= 2, paths=lesson_paths, total=len(spec.get("paths", {})))
    except Exception as exc:
        record("live_openapi_lessons", False, error=str(exc))

    login = httpx.post(
        f"{BASE}/api/auth/login",
        json={"email": "test.student@example.com", "password": PASSWORD},
        timeout=15,
    )
    token = login.json().get("access_token") if login.status_code == 200 else None
    record("auth_login", token is not None, status=login.status_code)
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    r = httpx.get(f"{BASE}/api/student/languages/lessons", headers=headers, timeout=60)
    body = r.json() if r.status_code == 200 else {}
    lessons = body.get("lessons") or []
    record(
        "lessons_list",
        r.status_code == 200 and body.get("level") and len(lessons) >= 5,
        status=r.status_code,
        level=body.get("level"),
        count=len(lessons),
        grammar=len([l for l in lessons if l.get("type") == "grammar"]),
        vocabulary=len([l for l in lessons if l.get("type") == "vocabulary"]),
    )

    if lessons:
        lid = lessons[0]["id"]
        r2 = httpx.get(f"{BASE}/api/student/languages/lessons/{lid}", headers=headers, timeout=30)
        detail = r2.json() if r2.status_code == 200 else {}
        record(
            "lesson_detail",
            r2.status_code == 200 and detail.get("id") == lid and bool(detail.get("practice")),
            status=r2.status_code,
            lesson_id=lid,
            practice_count=len(detail.get("practice") or []),
        )
    else:
        record("lesson_detail", False, error="no lessons from list")

    REPORT["all_ok"] = all(c["ok"] for c in REPORT["checks"])
    print(json.dumps(REPORT, indent=2, ensure_ascii=False))
    return 0 if REPORT["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
