"""Phase 8.1 runtime verification — vocabulary SM-2 routes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import httpx

BASE = "http://127.0.0.1:8000"
PASSWORD = "changeme"
REPORT: dict = {"phase": "8.1", "checks": []}


def record(name: str, ok: bool, **extra):
    REPORT["checks"].append({"name": name, "ok": ok, **extra})


def main() -> int:
    from app.main import app

    paths = [getattr(r, "path", "") for r in app.routes]
    sr_paths = [p for p in paths if p.endswith("/vocabulary/review") or p.endswith("/vocabulary/stats")]
    record("fastapi_vocab_sr_routes", len(sr_paths) >= 2, paths=sr_paths)

    try:
        spec = httpx.get(f"{BASE}/openapi.json", timeout=10).json()
        openapi_paths = [
            p
            for p in spec.get("paths", {})
            if p.endswith("/vocabulary/review") or p.endswith("/vocabulary/stats")
        ]
        record("live_openapi_vocab_sr", len(openapi_paths) >= 2, paths=openapi_paths, total=len(spec.get("paths", {})))
    except Exception as exc:
        record("live_openapi_vocab_sr", False, error=str(exc))

    login = httpx.post(
        f"{BASE}/api/auth/login",
        json={"email": "test.student@example.com", "password": PASSWORD},
        timeout=15,
    )
    token = login.json().get("access_token") if login.status_code == 200 else None
    record("auth_login", token is not None, status=login.status_code)
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    r = httpx.get(f"{BASE}/api/student/languages/vocabulary/review", headers=headers, timeout=30)
    body = r.json() if r.status_code == 200 else {}
    record(
        "vocabulary_review_get",
        r.status_code == 200 and "due_count" in body and "items" in body,
        status=r.status_code,
        due_count=body.get("due_count"),
        items=len(body.get("items") or []),
    )

    r2 = httpx.get(f"{BASE}/api/student/languages/vocabulary/stats", headers=headers, timeout=30)
    stats = r2.json() if r2.status_code == 200 else {}
    record(
        "vocabulary_stats_get",
        r2.status_code == 200 and "due_today" in stats,
        status=r2.status_code,
        stats=stats,
    )

    items = body.get("items") or []
    if items:
        vid = items[0]["vocabulary_id"]
        r3 = httpx.post(
            f"{BASE}/api/student/languages/vocabulary/review",
            headers=headers,
            json={"vocabulary_id": vid, "quality": 4},
            timeout=30,
        )
        res = r3.json() if r3.status_code == 200 else {}
        record(
            "vocabulary_review_submit",
            r3.status_code == 200 and res.get("new_status") in ("learning", "known", "new"),
            status=r3.status_code,
            result=res,
        )
    else:
        record("vocabulary_review_submit", True, skipped="no due items")

    REPORT["all_ok"] = all(c["ok"] for c in REPORT["checks"])
    print(json.dumps(REPORT, indent=2, ensure_ascii=False))
    return 0 if REPORT["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
