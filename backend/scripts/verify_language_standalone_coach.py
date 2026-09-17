"""Verify Phase 9.1 standalone Speaking Coach parity.

Usage (from backend/):
    python scripts/verify_language_standalone_coach.py
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
    router_src = (BACKEND / "app" / "api" / "router.py").read_text(encoding="utf-8")
    api_src = (BACKEND / "app" / "api" / "speaking_coach.py").read_text(encoding="utf-8")
    svc_src = (BACKEND / "app" / "services" / "speaking_coach_service.py").read_text(encoding="utf-8")
    vue_toggle = (ROOT / "src" / "components" / "language" / "LanguageSpeakingModeToggle.vue").read_text(
        encoding="utf-8"
    )
    vue_view = (ROOT / "src" / "views" / "student" / "languages" / "StudentLanguageSpeakingView.vue").read_text(
        encoding="utf-8"
    )
    vue_panel = (ROOT / "src" / "components" / "language" / "SpeakingCoachPanel.vue").read_text(encoding="utf-8")
    api_js = (ROOT / "src" / "api" / "language.js").read_text(encoding="utf-8")
    embedded = (BACKEND / "app" / "services" / "language_speaking_coach_service.py").read_text(encoding="utf-8")
    return {
        "router_mounted": "speaking_coach.router" in router_src,
        "api_turn": '"/turn"' in api_src and "CoachTurnOut" in api_src,
        "api_explanation": '"/turn/{turn_id}/explanation"' in api_src,
        "api_reset": '"/session/{session_id}"' in api_src and "reset_session" in api_src,
        "service_deferred": "generate_explanation_task" in svc_src and "conversation_memory" in svc_src,
        "embedded_preserved": "build_speaking_coach_result" in embedded,
        "toggle_coach_mode": 'value="coach"' in vue_toggle,
        "view_coach_panel": "SpeakingCoachPanel" in vue_view and "'coach'" in vue_view,
        "panel_tagged": "CoachTaggedText" in vue_panel and "coachTurn" in vue_panel,
        "api_js": all(x in api_js for x in ["coachTurn", "coachExplanation", "coachReset"]),
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
    coach_routes = sum(
        1
        for r in app.routes
        if getattr(r, "path", "").startswith("/api/speaking/coach")
    )

    mock_turn = {
        "turn_id": "abc123",
        "user_sentence_evaluated": "[error: I go] to school",
        "corrected_sentence": "[fix: I went] to school",
        "explanation": "",
        "ai_reply": "Good try! Where did you go?",
        "explanation_pending": True,
    }

    transport = ASGITransport(app=app)
    out: dict[str, bool | int] = {"openapi_count": openapi_count, "coach_routes": coach_routes}

    async with httpx.AsyncClient(transport=transport, base_url="http://t", timeout=30) as client:
        login = await client.post(
            "/api/auth/login",
            json={"email": default_test_email("auth_student"), "password": TEST_USER_PASSWORD},
        )
        out["login_ok"] = login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        with patch("app.api.speaking_coach.coach_turn", new=AsyncMock(return_value=mock_turn)):
            turn = await client.post(
                "/api/speaking/coach/turn",
                headers=headers,
                json={
                    "session_id": "verify-session",
                    "transcript": "I go to school yesterday",
                    "cefr_level": "B1",
                    "defer_explanation": True,
                },
            )
        out["turn_status_200"] = turn.status_code == 200
        out["turn_has_fields"] = all(
            k in turn.json()
            for k in ["turn_id", "user_sentence_evaluated", "corrected_sentence", "ai_reply", "explanation_pending"]
        )

        with patch("app.api.speaking_coach.get_explanation", return_value="Use past tense: went."):
            expl = await client.get("/api/speaking/coach/turn/abc123/explanation", headers=headers)
        out["explanation_status_200"] = expl.status_code == 200
        out["explanation_ready"] = expl.json().get("ready") is True

        with patch("app.api.speaking_coach.reset_session", new=AsyncMock()):
            reset = await client.delete("/api/speaking/coach/session/verify-session", headers=headers)
        out["reset_status_200"] = reset.status_code == 200

    return out


def main() -> int:
    static = static_checks()
    runtime = asyncio.run(runtime_checks())

    print("=== Phase 9.1 Standalone Speaking Coach ===\n")
    print("Static:")
    for k, v in static.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

    print("\nRuntime:")
    for k, v in runtime.items():
        if isinstance(v, bool):
            print(f"  {k}: {'PASS' if v else 'FAIL'}")
        else:
            print(f"  {k}: {v}")

    static_ok = all(static.values())
    runtime_ok = all(v for k, v in runtime.items() if k.endswith(("ok", "200", "fields", "ready")) or k == "coach_routes")
    openapi_ok = runtime.get("openapi_count", 0) >= 273 and runtime.get("coach_routes") == 3

    print(f"\nOpenAPI target (>=273, coach=3): {'PASS' if openapi_ok else 'FAIL'}")
    passed = sum(static.values()) + sum(
        1 for k, v in runtime.items() if isinstance(v, bool) and v
    ) + (1 if openapi_ok else 0)
    total = len(static) + sum(1 for v in runtime.values() if isinstance(v, bool)) + 1
    print(f"\n=== Results: {passed}/{total} checks passed ===")
    return 0 if static_ok and runtime_ok and openapi_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
