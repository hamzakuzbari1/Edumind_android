"""Verify Phase 9.3 Language TTS + Listening Assets parity.

Usage (from backend/):
    python scripts/verify_language_tts_listening.py
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
    api_src = (BACKEND / "app" / "api" / "language_student.py").read_text(encoding="utf-8")
    tts_src = (BACKEND / "app" / "services" / "language_tts_service.py").read_text(encoding="utf-8")
    content_src = (BACKEND / "app" / "services" / "language_content_service.py").read_text(encoding="utf-8")
    model_ok = (BACKEND / "app" / "models" / "language" / "tts_cache.py").is_file()
    mig_ok = (BACKEND / "alembic" / "versions" / "0047_lesson_tts_cache.py").is_file()
    placement_dir = ROOT / "public" / "language-assets" / "en" / "placement" / "listening"
    mp3_count = len(list(placement_dir.glob("*.mp3"))) if placement_dir.is_dir() else 0
    vue_src = (ROOT / "src" / "views" / "student" / "languages" / "StudentLanguageListeningView.vue").read_text(
        encoding="utf-8"
    )
    return {
        "tts_service": (BACKEND / "app" / "services" / "language_tts_service.py").is_file(),
        "tts_cache_model": model_ok,
        "tts_migration": mig_ok,
        "listening_tts_hook": "get_lesson_audio" in api_src and "if not audio_url" in api_src,
        "generate_and_cache": "generate_lesson_audio" in tts_src and "LanguageLessonAudioCache" in tts_src,
        "xtts_reuse": "TTS_WORKER_URL" in tts_src,
        "static_file_check": "_static_audio_file_exists" in content_src,
        "placement_mp3_count_10": mp3_count >= 10,
        "frontend_audio_player": "lesson.audio_url" in vue_src and "<audio" in vue_src,
        "gtts_installed": _gtts_available(),
    }


def _gtts_available() -> bool:
    try:
        import gtts  # noqa: F401

        return True
    except ImportError:
        return False


async def runtime_checks() -> dict[str, bool | int]:
    from httpx import ASGITransport
    import httpx
    from fastapi.openapi.utils import get_openapi

    for mod in list(sys.modules):
        if mod == "app" or mod.startswith("app."):
            del sys.modules[mod]

    from app.main import app
    from app.core.test_users import TEST_USER_PASSWORD, default_test_email
    from app.schemas.language import LanguageAccessOut

    openapi_count = len(get_openapi(title=app.title, version="1", routes=app.routes).get("paths", {}))

    mock_item = type(
        "Item",
        (),
        {
            "id": 99,
            "title": "Test Listening",
            "level": type("L", (), {"value": "A1"})(),
            "body_json": {"instructions": "Listen", "questions": []},
        },
    )()

    ready_access = LanguageAccessOut(subscribed=True, status="active", placement_completed=True)

    transport = ASGITransport(app=app)
    out: dict[str, bool | int] = {"openapi_count": openapi_count}

    async with httpx.AsyncClient(transport=transport, base_url="http://t", timeout=30) as client:
        login = await client.post(
            "/api/auth/login",
            json={"email": default_test_email("auth_student"), "password": TEST_USER_PASSWORD},
        )
        out["login_ok"] = login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        with patch(
            "app.services.language_access_service.build_language_access",
            new=AsyncMock(return_value=ready_access),
        ), patch(
            "app.api.language_student.get_listening_lesson",
            new=AsyncMock(return_value=(mock_item, None, None, False)),
        ), patch(
            "app.api.language_student.get_lesson_audio",
            new=AsyncMock(return_value={"public_url": "/uploads/language_audio/99/gtts.mp3", "voice_source": "gtts"}),
        ), patch(
            "app.api.language_student.lesson_body_for_student",
            return_value={"instructions": "Listen", "questions": []},
        ):
            resp = await client.get("/api/student/languages/listening/99", headers=headers)

        out["listening_detail_not_404"] = resp.status_code != 404
        out["listening_tts_injected"] = (
            resp.status_code == 200
            and resp.json().get("audio_available") is True
            and "/uploads/" in (resp.json().get("audio_url") or "")
        )

        placement = ROOT / "public" / "language-assets" / "en" / "placement" / "listening" / "q1.mp3"
        out["placement_q1_on_disk"] = placement.is_file()

    return out


def main() -> int:
    static = static_checks()
    runtime = asyncio.run(runtime_checks())

    print("=== Phase 9.3 Language TTS + Listening ===\n")
    print("Static:")
    for k, v in static.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

    print("\nRuntime:")
    for k, v in runtime.items():
        if isinstance(v, bool):
            print(f"  {k}: {'PASS' if v else 'FAIL'}")
        else:
            print(f"  {k}: {v}")

    openapi_ok = runtime.get("openapi_count", 0) >= 274
    print(f"\nOpenAPI unchanged (>=274): {'PASS' if openapi_ok else 'FAIL'}")

    bool_checks = [v for v in static.values()] + [v for k, v in runtime.items() if isinstance(v, bool)]
    passed = sum(bool_checks) + (1 if openapi_ok else 0)
    total = len(bool_checks) + 1
    print(f"\n=== Results: {passed}/{total} checks passed ===")
    ok = all(static.values()) and all(v for k, v in runtime.items() if isinstance(v, bool)) and openapi_ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
