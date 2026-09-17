"""Phase 8.0 runtime verification — promotion test routes and flows."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import httpx

BASE = "http://127.0.0.1:8000"
PASSWORD = "changeme"
REPORT: dict = {"phase": "8.0", "checks": []}


def record(name: str, ok: bool, **extra):
    REPORT["checks"].append({"name": name, "ok": ok, **extra})


def main() -> int:
    from app.main import app

    paths = [getattr(r, "path", "") for r in app.routes]
    promo_paths = [p for p in paths if "promotion-test" in p]
    record("fastapi_promotion_routes", len(promo_paths) == 2, count=len(promo_paths), paths=promo_paths)

    try:
        spec = httpx.get(f"{BASE}/openapi.json", timeout=10).json()
        openapi_paths = [p for p in spec.get("paths", {}) if "promotion-test" in p]
        total = len(spec.get("paths", {}))
        record("live_openapi_promotion", len(openapi_paths) == 2, paths=openapi_paths, total_routes=total)
    except Exception as exc:
        record("live_openapi_promotion", False, error=str(exc))

    login = httpx.post(
        f"{BASE}/api/auth/login",
        json={"email": "test.student@example.com", "password": PASSWORD},
        timeout=15,
    )
    token = login.json().get("access_token") if login.status_code == 200 else None
    record("auth_login", token is not None, status=login.status_code)
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    r = httpx.get(f"{BASE}/api/student/languages/promotion-test", headers=headers, timeout=30)
    body = r.json() if r.status_code == 200 else {}
    record(
        "promotion_test_get",
        r.status_code == 200 and bool(body.get("test_id")) and len(body.get("questions") or []) >= 4,
        status=r.status_code,
        level=body.get("level"),
        next_level=body.get("next_level"),
        questions=len(body.get("questions") or []),
    )

    test_id = body.get("test_id")
    questions = body.get("questions") or []
    if test_id and questions:
        wrong = {str(q["id"]): (q["id"] + 1) % 4 for q in questions}
        r2 = httpx.post(
            f"{BASE}/api/student/languages/promotion-test/submit",
            headers=headers,
            json={"test_id": test_id, "answers": wrong},
            timeout=30,
        )
        res = r2.json() if r2.status_code == 200 else {}
        record(
            "promotion_failure_flow",
            r2.status_code == 200 and not res.get("passed") and not res.get("promoted"),
            status=r2.status_code,
            score=res.get("score_percent"),
        )
    else:
        record("promotion_failure_flow", False, error="no test_id from GET")

    # Success flow with level advancement is covered by verify_language_promotion.py (DB rollback).
    REPORT["all_ok"] = all(c["ok"] for c in REPORT["checks"])
    print(json.dumps(REPORT, indent=2, ensure_ascii=False))
    return 0 if REPORT["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
