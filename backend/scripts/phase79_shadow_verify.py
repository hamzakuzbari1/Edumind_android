"""Phase 7.9 runtime verification — shadowing routes and authenticated list."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import httpx

BASE = "http://127.0.0.1:8000"
PASSWORD = "changeme"
REPORT: dict = {"phase": "7.9", "checks": []}


def record(name: str, ok: bool, **extra):
    REPORT["checks"].append({"name": name, "ok": ok, **extra})


def main() -> int:
    from app.main import app

    paths = [getattr(r, "path", "") for r in app.routes]
    shadow_paths = [p for p in paths if "speaking/shadow" in p]
    record("fastapi_shadow_routes", len(shadow_paths) == 2, count=len(shadow_paths), paths=shadow_paths)

    try:
        spec = httpx.get(f"{BASE}/openapi.json", timeout=10).json()
        openapi_paths = [p for p in spec.get("paths", {}) if "speaking/shadow" in p]
        total = len(spec.get("paths", {}))
        record("live_openapi_shadow", len(openapi_paths) == 2, paths=openapi_paths, total_routes=total)
    except Exception as exc:
        record("live_openapi_shadow", False, error=str(exc))

    token = None
    try:
        login = httpx.post(
            f"{BASE}/api/auth/login",
            json={"email": "test.student@example.com", "password": PASSWORD},
            timeout=15,
        )
        token = login.json().get("access_token") if login.status_code == 200 else None
        record("auth_login", token is not None, status=login.status_code)
    except Exception as exc:
        record("auth_login", False, error=str(exc))

    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = httpx.get(f"{BASE}/api/student/languages/speaking/shadow/sentences", headers=headers, timeout=30)
        body = r.json() if r.status_code == 200 else {}
        record(
            "shadow_sentences",
            r.status_code == 200 and len(body.get("sentences") or []) >= 5,
            status=r.status_code,
            level=body.get("level"),
            count=len(body.get("sentences") or []),
        )
    except Exception as exc:
        record("shadow_sentences", False, error=str(exc))

    REPORT["all_ok"] = all(c["ok"] for c in REPORT["checks"])
    print(json.dumps(REPORT, indent=2, ensure_ascii=False))
    return 0 if REPORT["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
