"""Verify lesson chat uses LESSON_CHAT_MODEL; other features keep GEMINI_MODEL.

Usage (from backend/):
    python scripts/verify_lesson_chat_model_separation.py
"""

from __future__ import annotations

import asyncio
import inspect
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SAMPLE_LESSON = """
الشبكات

الشبكة هي مجموعة أجهزة متصلة لتبادل البيانات بينها باستخدام بروتوكولات موحدة.
TCP بروتوكول موثوق يرسل البيانات بالترتيب ويضمن وصول الحزم بشكل صحيح.
IP مسؤول عن التوجيه بين الشبكات وتحديد عنوان كل جهاز على الشبكة.
الميزات الرئيسية للشبكات: مشاركة الموارد، التواصل، ونقل البيانات بكفاءة.
""".strip()

SAMPLE_QUESTION = "ما هو بروتوكول TCP؟"


def _configured_models() -> dict[str, str]:
    from app.core.config import get_settings

    settings = get_settings()
    return {
        "lesson_chat": settings.LESSON_CHAT_MODEL,
        "quiz": settings.GEMINI_MODEL,
        "planner": settings.GEMINI_MODEL,
        "speaking": settings.GEMINI_MODEL,
        "ocr_and_other": settings.GEMINI_MODEL,
    }


def _source_uses_model(function, *, expect: str, forbid: str | None = None) -> bool:
    source = inspect.getsource(function)
    if expect not in source:
        return False
    if forbid and forbid in source:
        return False
    return True


def _static_checks() -> dict[str, bool]:
    from app.services import ai_service
    from app.services.quiz_service import _call_gemini_text

    models = _configured_models()
    return {
        "lesson_chat_config_is_flash_lite": models["lesson_chat"] == "gemini-3.1-flash-lite",
        "shared_gemini_model_is_2_5_flash": models["quiz"] == "gemini-2.5-flash",
        "generate_tutor_reply_uses_lesson_chat_model": _source_uses_model(
            ai_service.generate_tutor_reply,
            expect="settings.LESSON_CHAT_MODEL",
            forbid="settings.GEMINI_MODEL",
        ),
        "generate_planner_uses_gemini_model": _source_uses_model(
            ai_service.generate_planner_interpretation,
            expect="settings.GEMINI_MODEL",
        ),
        "generate_gemini_json_uses_gemini_model": _source_uses_model(
            ai_service.generate_gemini_json,
            expect="settings.GEMINI_MODEL",
        ),
        "quiz_service_uses_gemini_model": "settings.GEMINI_MODEL" in inspect.getsource(_call_gemini_text)
        and "LESSON_CHAT_MODEL" not in inspect.getsource(_call_gemini_text),
    }


async def _live_lesson_chat_model() -> dict:
    import types

    from app.core.config import get_settings
    from app.services import ai_service

    settings = get_settings()
    captured: list[str] = []

    class _RecordingModel:
        def __init__(self, model_name: str, **kwargs):
            captured.append(model_name)

        def generate_content(self, *args, **kwargs):
            response = MagicMock()
            response.text = "**TCP** بروتوكول موثوق يرسل البيانات بالترتيب."
            response.candidates = []
            return response

    fake_genai = types.ModuleType("google.generativeai")
    fake_genai.configure = lambda *args, **kwargs: None
    fake_genai.GenerativeModel = _RecordingModel
    fake_google = types.ModuleType("google")
    fake_google.generativeai = fake_genai

    with patch.dict(sys.modules, {"google": fake_google, "google.generativeai": fake_genai}):
        with patch.object(ai_service.settings, "GEMINI_API_KEY", "test-key"):
            with patch.object(ai_service.settings, "LLM_PROVIDER", "gemini"):
                reply = await ai_service.generate_tutor_reply(
                    SAMPLE_QUESTION,
                    [SAMPLE_LESSON],
                    persona_prompt="أنت معلّم مساعد.",
                    subject="علوم الحاسوب",
                    grade="10",
                )

    return {
        "captured_model": captured[-1] if captured else None,
        "expected_model": settings.LESSON_CHAT_MODEL,
        "reply_preview": (reply or "")[:200],
        "live_ok": bool(captured) and captured[-1] == settings.LESSON_CHAT_MODEL,
    }


async def main() -> None:
    from app.core.config import get_settings

    settings = get_settings()
    models = _configured_models()
    static = _static_checks()

    print("=== Configured models ===")
    print(f"  lesson_chat : {models['lesson_chat']}")
    print(f"  quiz        : {models['quiz']}")
    print(f"  planner     : {models['planner']}")
    print(f"  speaking    : {models['speaking']}")

    print("\n=== Static separation checks ===")
    for key, ok in static.items():
        print(f"  {'PASS' if ok else 'FAIL'}: {key}")

    live = await _live_lesson_chat_model()
    print("\n=== Live lesson chat (patched GenerativeModel) ===")
    print(f"  captured model : {live['captured_model']}")
    print(f"  expected model : {live['expected_model']}")
    print(f"  {'PASS' if live['live_ok'] else 'FAIL'}: lesson chat uses LESSON_CHAT_MODEL")
    print(f"  reply preview  : {live['reply_preview']}")

    summary = {
        "configured_models": models,
        "static_checks": static,
        "live_lesson_chat": live,
        "expected": {
            "lesson_chat": "gemini-3.1-flash-lite",
            "everything_else": "gemini-2.5-flash",
        },
    }

    out = Path(__file__).resolve().parent / "lesson_chat_model_separation_results.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWritten: {out}")


if __name__ == "__main__":
    asyncio.run(main())
