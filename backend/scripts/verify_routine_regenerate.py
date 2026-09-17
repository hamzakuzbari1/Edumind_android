"""Verify Phase 9.2 Routine Regenerate parity.

Usage (from backend/):
    python scripts/verify_routine_regenerate.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent


def static_checks() -> dict[str, bool]:
    api_src = (BACKEND / "app" / "api" / "routine.py").read_text(encoding="utf-8")
    svc_src = (BACKEND / "app" / "services" / "routine_service.py").read_text(encoding="utf-8")
    js_src = (ROOT / "src" / "api" / "routine.js").read_text(encoding="utf-8")
    return {
        "regenerate_route": '"/regenerate"' in api_src and "regenerate_schedule" in api_src,
        "regenerate_service": "async def regenerate_student_routine" in svc_src,
        "ensure_english": "async def ensure_english_routine" in svc_src,
        "week_read_only": "ensure_english_routine" not in api_src.split("@router.get(\"/week\")")[1].split("@router.post")[0],
        "renew_uses_service": "regenerate_student_routine" in api_src.split("renew_week")[1][:600],
        "api_js": "regenerateSchedule" in js_src and "/student/routine/regenerate" in js_src,
    }


async def runtime_checks() -> dict[str, bool | int]:
    from httpx import ASGITransport
    import httpx
    from fastapi.openapi.utils import get_openapi

    for mod in list(sys.modules):
        if mod == "app" or mod.startswith("app."):
            del sys.modules[mod]

    from app.main import app
    from app.core.test_users import TEST_USER_PASSWORD, default_test_email

    openapi_count = len(get_openapi(title=app.title, version="1", routes=app.routes).get("paths", {}))
    regen_routes = [
        getattr(r, "path", "")
        for r in app.routes
        if getattr(r, "path", "") == "/api/student/routine/regenerate"
    ]

    mock_days = {"0": [{"start": "08:00", "end": "09:00", "title": "Math", "type": "study"}]}
    mock_result = {
        "ok": True,
        "regenerated": True,
        "slots_saved": 7,
        "reason": "success",
    }

    transport = ASGITransport(app=app)
    out: dict[str, bool | int] = {
        "openapi_count": openapi_count,
        "regenerate_route_count": len(regen_routes),
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://t", timeout=30) as client:
        login = await client.post(
            "/api/auth/login",
            json={"email": default_test_email("auth_student"), "password": TEST_USER_PASSWORD},
        )
        out["login_ok"] = login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        with patch(
            "app.api.routine.get_week_slots",
            new=AsyncMock(return_value=mock_days),
        ), patch(
            "app.api.routine.week_schedule_contains_arabic",
            return_value=False,
        ), patch(
            "app.api.routine.get_weak_subjects",
            new=AsyncMock(return_value=["math"]),
        ), patch(
            "app.api.routine.regenerate_student_routine",
            new=AsyncMock(return_value=mock_result),
        ), patch(
            "app.api.routine.get_or_create_routine_profile",
            new=AsyncMock(return_value=type("P", (), {"id": 1, "student_id": 1, "onboarding_complete": True})()),
        ):
            resp = await client.post("/api/student/routine/regenerate", headers=headers)

        out["regenerate_not_404"] = resp.status_code != 404
        out["regenerate_status_200"] = resp.status_code == 200
        body = resp.json()
        out["regenerate_payload"] = body.get("regenerated") is True and "days" in body and body.get("slots_saved") == 7

        empty_days = {str(i): [] for i in range(7)}
        with patch(
            "app.api.routine.get_week_slots",
            new=AsyncMock(return_value=empty_days),
        ), patch(
            "app.api.routine.get_or_create_routine_profile",
            new=AsyncMock(return_value=type("P", (), {"id": 1, "student_id": 1})()),
        ):
            empty = await client.post("/api/student/routine/regenerate", headers=headers)
        out["empty_schedule_400"] = empty.status_code == 400

    return out


def main() -> int:
    static = static_checks()
    runtime = asyncio.run(runtime_checks())

    print("=== Phase 9.2 Routine Regenerate ===\n")
    print("Static:")
    for k, v in static.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

    print("\nRuntime:")
    for k, v in runtime.items():
        if isinstance(v, bool):
            print(f"  {k}: {'PASS' if v else 'FAIL'}")
        else:
            print(f"  {k}: {v}")

    openapi_ok = runtime.get("openapi_count", 0) >= 274 and runtime.get("regenerate_route_count") == 1
    print(f"\nOpenAPI target (>=274, regenerate=1): {'PASS' if openapi_ok else 'FAIL'}")

    bool_checks = [v for v in static.values()] + [v for v in runtime.values() if isinstance(v, bool)]
    passed = sum(bool_checks) + (1 if openapi_ok else 0)
    total = len(bool_checks) + 1
    print(f"\n=== Results: {passed}/{total} checks passed ===")
    ok = all(static.values()) and all(v for k, v in runtime.items() if isinstance(v, bool)) and openapi_ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
