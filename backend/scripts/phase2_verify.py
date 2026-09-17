"""Phase 2 verification — conversation backend services and AI stack."""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import time
import traceback
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import httpx

BASE = "http://127.0.0.1:8000"
PASSWORD = "changeme"
REPORT: dict = {"checks": []}


def record(name: str, ok: bool, **extra):
    REPORT["checks"].append({"name": name, "ok": ok, **extra})


def check_imports() -> None:
    modules = [
        "app.services.language_conversation_service",
        "app.services.language_conversation_ai_service",
        "app.services.language_conversation_prompts",
        "app.services.language_conversation_correction",
        "app.services.language_transcription_service",
        "app.services.language_reply_tts_service",
        "app.services.language_speaking_evolution_service",
        "app.services.language_grammar_service",
        "app.services.language_conversation_tts_task",
    ]
    failed = []
    for mod in modules:
        try:
            __import__(mod)
        except Exception as exc:
            failed.append({"module": mod, "error": str(exc)})
    record("service_imports", not failed, failed=failed, count=len(modules))


def check_fastapi_startup() -> None:
    warnings: list[str] = []
    try:
        from app.main import app

        routes = [getattr(r, "path", "") for r in app.routes]
        conv_routes = [p for p in routes if "speaking/conversation" in p]
        record(
            "fastapi_startup",
            bool(conv_routes),
            conversation_routes=conv_routes,
            route_count=len(routes),
        )
    except Exception as exc:
        record("fastapi_startup", False, error=str(exc), traceback=traceback.format_exc()[-800:])


async def check_gemini_conversation() -> None:
    from app.services.language_conversation_ai_service import generate_conversation_turn

    try:
        result = await generate_conversation_turn(
            transcript="Hello, my name is Hamza and I like studying science.",
            effective_level="A2",
            grammar_hints=[],
            history=[],
        )
        ok = bool(result.get("reply")) and bool(result.get("coaching_note_ar"))
        record(
            "gemini_conversation",
            ok,
            reply_preview=(result.get("reply") or "")[:120],
            estimated_cefr=result.get("estimated_cefr"),
            coaching_note_ar=result.get("coaching_note_ar"),
        )
    except Exception as exc:
        record("gemini_conversation", False, error=str(exc))


async def check_whisper_transcription() -> None:
    from app.core.config import get_settings
    from app.services.language_transcription_service import transcribe_english_audio

    settings = get_settings()
    sample = BACKEND / "scripts" / "_tts_verify_out" / "arabic_test.wav"
    if not sample.is_file():
        record("whisper_transcription", False, error=f"missing sample {sample}")
        return
    data = sample.read_bytes()
    try:
        result = await transcribe_english_audio(data, suffix=".wav")
        ok = result.engine not in ("", "none", "disabled", "error") and settings.ENABLE_WHISPER
        record(
            "whisper_transcription",
            ok,
            engine=result.engine,
            model=result.model,
            text_preview=(result.text or "")[:80],
            enable_whisper=settings.ENABLE_WHISPER,
        )
    except Exception as exc:
        record("whisper_transcription", False, error=str(exc))


async def check_xtts_reply() -> None:
    from app.core.config import get_settings
    from app.services.tts_service import synthesize_cloned_speech

    settings = get_settings()
    speaker = settings.LANGUAGE_CONVERSATION_SPEAKER_WAV
    out = Path(tempfile.gettempdir()) / f"phase2_xtts_{uuid.uuid4().hex}.wav"
    try:
        ok = await synthesize_cloned_speech(
            "Hello, this is a short English reply test.",
            speaker,
            language="en",
            output_path=out,
        )
        size = out.stat().st_size if out.exists() else 0
        record(
            "xtts_reply",
            ok and size > 1000,
            bytes=size,
            speaker_wav=speaker,
            enable_tts=settings.ENABLE_TTS,
            worker_url=settings.TTS_WORKER_URL,
        )
    except Exception as exc:
        record("xtts_reply", False, error=str(exc))
    finally:
        out.unlink(missing_ok=True)


def check_http_regressions() -> None:
    try:
        health = httpx.get(f"{BASE}/health", timeout=15)
        record("regression_health", health.status_code == 200, status=health.status_code)
    except Exception as exc:
        record("regression_health", False, error=str(exc))
        return

    # speaking exercises (unchanged)
    try:
        login = httpx.post(
            f"{BASE}/api/auth/login",
            json={"email": "test.student@example.com", "password": PASSWORD},
            timeout=30,
        )
        token = login.json().get("access_token") if login.status_code == 200 else None
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        speaking = httpx.get(f"{BASE}/api/student/languages/speaking", headers=headers, timeout=30)
        prompts = speaking.json().get("prompts", []) if speaking.status_code == 200 else []
        record(
            "regression_speaking_exercises",
            speaking.status_code == 200 and len(prompts) > 0,
            status=speaking.status_code,
            prompts_count=len(prompts),
        )
        conv = httpx.get(f"{BASE}/api/student/languages/speaking/conversation", headers=headers, timeout=30)
        record(
            "conversation_state_endpoint",
            conv.status_code == 200,
            status=conv.status_code,
            welcome_hint=conv.json().get("welcome_hint") if conv.status_code == 200 else None,
        )
    except Exception as exc:
        record("regression_speaking_exercises", False, error=str(exc))

    # lesson chat (processed lesson 88)
    try:
        login = httpx.post(
            f"{BASE}/api/auth/login",
            json={"email": "test.student@example.com", "password": PASSWORD},
            timeout=30,
        )
        token = login.json()["access_token"]
        chat = httpx.post(
            f"{BASE}/api/student/chat",
            json={"lesson_id": 88, "message": "ما موضوع الدرس؟ جملة واحدة."},
            headers={"Authorization": f"Bearer {token}"},
            timeout=120,
        )
        body = chat.json() if chat.status_code == 200 else {}
        ai = [m for m in body.get("messages", []) if m.get("role") == "ai"]
        record(
            "regression_lesson_chat",
            chat.status_code == 200 and bool(ai),
            status=chat.status_code,
            ai_preview=(ai[-1].get("text") or "")[:80] if ai else None,
        )
    except Exception as exc:
        record("regression_lesson_chat", False, error=str(exc))

    # routine AI parse (lightweight)
    try:
        login = httpx.post(
            f"{BASE}/api/auth/login",
            json={"email": "test.student@example.com", "password": PASSWORD},
            timeout=30,
        )
        token = login.json()["access_token"]
        routine = httpx.post(
            f"{BASE}/api/student/routine/chat",
            json={"message": "أضف حصة رياضيات يوم الثلاثاء الساعة 4"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=120,
        )
        record(
            "regression_routine_ai",
            routine.status_code == 200,
            status=routine.status_code,
        )
    except Exception as exc:
        record("regression_routine_ai", False, error=str(exc))

    # quiz generation
    try:
        login = httpx.post(
            f"{BASE}/api/auth/login",
            json={"email": "test.student@example.com", "password": PASSWORD},
            timeout=30,
        )
        token = login.json()["access_token"]
        quiz = httpx.post(
            f"{BASE}/api/student/lesson/88/quiz/regenerate",
            headers={"Authorization": f"Bearer {token}"},
            timeout=180,
        )
        body = quiz.json() if quiz.status_code == 200 else {}
        questions = body.get("quizQuestions", body if isinstance(body, list) else [])
        record(
            "regression_quiz_generation",
            quiz.status_code == 200 and isinstance(questions, list) and len(questions) > 0,
            status=quiz.status_code,
            questions_count=len(questions) if isinstance(questions, list) else 0,
        )
    except Exception as exc:
        record("regression_quiz_generation", False, error=str(exc))


async def main() -> int:
    check_imports()
    check_fastapi_startup()
    await check_gemini_conversation()
    await check_whisper_transcription()
    await check_xtts_reply()
    check_http_regressions()
    REPORT["all_ok"] = all(c["ok"] for c in REPORT["checks"])
    out = BACKEND / "scripts" / "phase2_verify_report.json"
    out.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(REPORT, ensure_ascii=False, indent=2))
    return 0 if REPORT["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
