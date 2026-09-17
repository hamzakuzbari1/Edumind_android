"""Verify Phase 10.0 Lesson Chat Teacher Avatar + Voice Status parity.

Usage (from backend/):
    python scripts/verify_lesson_chat_avatar.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent


def static_checks() -> dict[str, bool]:
    avatar = ROOT / "src" / "components" / "student" / "LessonChatTeacherAvatar.vue"
    panel = (ROOT / "src" / "components" / "student" / "ChatPanel.vue").read_text(encoding="utf-8")
    bubble = (ROOT / "src" / "components" / "student" / "ChatBubble.vue").read_text(encoding="utf-8")
    typing = (ROOT / "src" / "components" / "student" / "TypingIndicator.vue").read_text(encoding="utf-8")
    view = (ROOT / "src" / "views" / "student" / "StudentLessonView.vue").read_text(encoding="utf-8")
    composable = (ROOT / "src" / "composables" / "useAiChat.js").read_text(encoding="utf-8")
    schema = (BACKEND / "app" / "schemas" / "student.py").read_text(encoding="utf-8")
    student_api = (BACKEND / "app" / "api" / "student.py").read_text(encoding="utf-8")
    return {
        "avatar_component": avatar.is_file(),
        "chat_panel_avatar": "LessonChatTeacherAvatar" in panel and "voiceTtsAvailable" in panel,
        "chat_bubble_avatar": "LessonChatTeacherAvatar" in bubble and "teacherName" in bubble,
        "typing_avatar": "LessonChatTeacherAvatar" in typing and "teacherName" in typing,
        "lesson_view_wiring": all(
            x in view
            for x in ["voiceTtsAvailable", "voiceTtsMessage", "teacher-image-url", "applyVoiceTtsStatus"]
        ),
        "use_ai_chat_voice": "voiceTtsAvailable" in composable and "applyVoiceTtsStatus" in composable,
        "schema_fields": "voiceTtsAvailable" in schema and "voiceTtsMessage" in schema,
        "api_voice_status": "_lesson_voice_tts_status" in student_api,
        "tts_worker_service": (BACKEND / "app" / "services" / "tts_worker_service.py").is_file(),
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
    from app.schemas.student import ChatResponse

    openapi_count = len(get_openapi(title=app.title, version="1", routes=app.routes).get("paths", {}))

    transport = ASGITransport(app=app)
    out: dict[str, bool | int] = {"openapi_count": openapi_count}

    async with httpx.AsyncClient(transport=transport, base_url="http://t", timeout=30) as client:
        login = await client.post(
            "/api/auth/login",
            json={"email": default_test_email("auth_student"), "password": TEST_USER_PASSWORD},
        )
        out["login_ok"] = login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        mock_response = ChatResponse(
            reply="مرحباً",
            messages=[],
            question="hello",
            voiceTtsAvailable=False,
            voiceTtsMessage="تشغيل الصوت معطّل على هذا الخادم.",
        )
        with patch("app.api.student._lesson_for_chat", new=AsyncMock(return_value=MagicMock(id=1))), patch(
            "app.api.student._run_chat_turn",
            new=AsyncMock(return_value=mock_response),
        ):
            chat = await client.post(
                "/api/student/chat",
                headers=headers,
                json={"lesson_id": 1, "message": "hello"},
            )
        body = chat.json()
        out["chat_voice_fields"] = (
            chat.status_code == 200
            and body.get("voiceTtsAvailable") is False
            and "voiceTtsMessage" in body
        )

    from app.api.student import _lesson_voice_tts_status
    from app.core.config import get_settings

    mock_lesson = MagicMock(voice_path=None, teacher_id=1)
    mock_db = AsyncMock()
    settings = get_settings()
    original = settings.ENABLE_TTS
    try:
        settings.ENABLE_TTS = False
        available, message = await _lesson_voice_tts_status(mock_db, mock_lesson)
    finally:
        settings.ENABLE_TTS = original
    out["voice_status_disabled"] = available is False and bool(message)

    out["openapi_unchanged"] = openapi_count == 274
    return out


def main() -> int:
    static = static_checks()
    runtime = asyncio.run(runtime_checks())

    print("=== Phase 10.0 Lesson Chat Avatar + Voice Status ===\n")
    print("Static:")
    for k, v in static.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

    print("\nRuntime:")
    for k, v in runtime.items():
        if isinstance(v, bool):
            print(f"  {k}: {'PASS' if v else 'FAIL'}")
        else:
            print(f"  {k}: {v}")

    bool_checks = list(static.values()) + [v for k, v in runtime.items() if isinstance(v, bool)]
    passed = sum(bool_checks)
    total = len(bool_checks)
    print(f"\n=== Results: {passed}/{total} checks passed ===")
    ok = all(bool_checks)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
