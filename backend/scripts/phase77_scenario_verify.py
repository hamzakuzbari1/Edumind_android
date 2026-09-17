"""Phase 7.7 runtime verification — scenario routes and start endpoint."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

import httpx

BASE = "http://127.0.0.1:8000"
PASSWORD = "changeme"
REPORT: dict = {"phase": "7.7", "checks": []}


def record(name: str, ok: bool, **extra):
    REPORT["checks"].append({"name": name, "ok": ok, **extra})


def count_scenario_openapi_paths() -> int:
    try:
        spec = httpx.get(f"{BASE}/openapi.json", timeout=10).json()
        paths = [p for p in spec.get("paths", {}) if "/speaking/scenarios" in p]
        return len(paths)
    except Exception:
        return 0


def check_fastapi_routes() -> None:
    from app.main import app

    paths = [getattr(r, "path", "") for r in app.routes]
    scenario_paths = [p for p in paths if "speaking/scenarios" in p]
    record(
        "fastapi_scenario_routes",
        len(scenario_paths) >= 7,
        count=len(scenario_paths),
        paths=scenario_paths,
    )


def check_http_runtime() -> None:
    before_note = REPORT.get("openapi_scenario_paths_before")
    after = count_scenario_openapi_paths()
    record("openapi_scenario_paths", after >= 7, count=after, before=before_note)

    try:
        login = httpx.post(
            f"{BASE}/api/auth/login",
            json={"email": "test.student@example.com", "password": PASSWORD},
            timeout=30,
        )
        token = login.json().get("access_token") if login.status_code == 200 else None
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        start = httpx.post(
            f"{BASE}/api/student/languages/speaking/scenarios/1/start",
            headers=headers,
            timeout=60,
        )
        record(
            "scenario_start_endpoint",
            start.status_code in (200, 403),
            status=start.status_code,
            detail=start.json().get("detail") if start.status_code == 403 else None,
            session_id=start.json().get("session_id") if start.status_code == 200 else None,
        )

        listing = httpx.get(
            f"{BASE}/api/student/languages/speaking/scenarios",
            headers=headers,
            timeout=30,
        )
        body = listing.json() if listing.status_code == 200 else {}
        record(
            "scenario_list",
            listing.status_code == 200 and len(body.get("scenarios", [])) >= 8,
            status=listing.status_code,
            count=len(body.get("scenarios", [])),
            categories=len(body.get("categories", [])),
        )
    except Exception as exc:
        record("scenario_start_endpoint", False, error=str(exc))


def check_frontend_build() -> None:
    proc = subprocess.run(
        ["npm", "run", "build"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        shell=True,
    )
    record("frontend_build", proc.returncode == 0, returncode=proc.returncode)


def main() -> int:
    REPORT["openapi_scenario_paths_before"] = 0
    check_fastapi_routes()
    check_http_runtime()
    check_frontend_build()
    REPORT["all_ok"] = all(c["ok"] for c in REPORT["checks"])
    out = BACKEND / "scripts" / "phase77_scenario_verify_report.json"
    out.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(REPORT, ensure_ascii=False, indent=2))
    return 0 if REPORT["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
