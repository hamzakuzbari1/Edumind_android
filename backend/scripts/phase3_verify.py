"""Phase 3 verification — speaking conversation frontend + end-to-end API."""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

import httpx

BASE = "http://127.0.0.1:8000"
PASSWORD = "changeme"
REPORT: dict = {"phase": 3, "checks": []}


def record(name: str, ok: bool, **extra):
    REPORT["checks"].append({"name": name, "ok": ok, **extra})


def login_token() -> str | None:
    login = httpx.post(
        f"{BASE}/api/auth/login",
        json={"email": "test.student@example.com", "password": PASSWORD},
        timeout=30,
    )
    if login.status_code != 200:
        return None
    return login.json().get("access_token")


def check_frontend_build() -> None:
    try:
        proc = subprocess.run(
            ["npm", "run", "build"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
            shell=True,
        )
        record(
            "frontend_build",
            proc.returncode == 0,
            returncode=proc.returncode,
            stderr_tail=(proc.stderr or "")[-500:] if proc.returncode != 0 else None,
        )
    except Exception as exc:
        record("frontend_build", False, error=str(exc))


def check_frontend_files() -> None:
    required = [
        ROOT / "src/composables/useLanguageConversation.js",
        ROOT / "src/components/language/LanguageSpeakingModeToggle.vue",
        ROOT / "src/components/language/LanguageSpeakingConversationPanel.vue",
        ROOT / "src/components/language/LanguageSpeakingLevelStrip.vue",
        ROOT / "src/components/language/LanguageSpeakingTurnEvaluation.vue",
        ROOT / "src/components/language/LanguageSpeakingCorrectionBlock.vue",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    view = (ROOT / "src/views/student/languages/StudentLanguageSpeakingView.vue").read_text(encoding="utf-8")
    toggle = (ROOT / "src/components/language/LanguageSpeakingModeToggle.vue").read_text(encoding="utf-8")
    has_toggle = (
        "LanguageSpeakingModeToggle" in view
        and "تمارين التحدث" in toggle
        and "محادثة ذكية" in toggle
    )
    has_panel = "LanguageSpeakingConversationPanel" in view
    has_exercises = "fetchSpeakingPrompts" in view and "submitSpeakingPractice" in view
    record(
        "frontend_files",
        not missing and has_toggle and has_panel and has_exercises,
        missing=missing,
        has_mode_toggle=has_toggle,
        has_conversation_panel=has_panel,
        exercises_preserved=has_exercises,
    )


def check_speaking_exercises(headers: dict) -> None:
    speaking = httpx.get(f"{BASE}/api/student/languages/speaking", headers=headers, timeout=30)
    prompts = speaking.json().get("prompts", []) if speaking.status_code == 200 else []
    record(
        "speaking_exercises",
        speaking.status_code == 200 and len(prompts) > 0,
        status=speaking.status_code,
        prompts_count=len(prompts),
    )
    if prompts:
        pid = prompts[0]["id"]
        detail = httpx.get(f"{BASE}/api/student/languages/speaking/{pid}", headers=headers, timeout=30)
        record(
            "speaking_exercise_detail",
            detail.status_code == 200 and bool(detail.json().get("prompt")),
            status=detail.status_code,
            prompt_id=pid,
        )


def check_conversation_state(headers: dict) -> None:
    conv = httpx.get(f"{BASE}/api/student/languages/speaking/conversation", headers=headers, timeout=30)
    body = conv.json() if conv.status_code == 200 else {}
    hint = body.get("welcome_hint") or ""
    record(
        "conversation_state",
        conv.status_code == 200 and ("تحدّث" in hint or (body.get("turn_count") or 0) > 0),
        status=conv.status_code,
        welcome_hint=hint or None,
        turn_count=body.get("turn_count"),
    )
    prog = httpx.get(
        f"{BASE}/api/student/languages/speaking/conversation/progress",
        headers=headers,
        timeout=30,
    )
    record("conversation_progress", prog.status_code == 200, status=prog.status_code)


def check_conversation_turn_e2e(headers: dict) -> None:
    """Post a short WAV turn — exercises Gemini + Whisper + optional XTTS."""
    sample = BACKEND / "scripts" / "_tts_verify_out" / "arabic_test.wav"
    if not sample.is_file():
        record("conversation_turn_e2e", False, error=f"missing audio sample {sample}")
        return
    try:
        with sample.open("rb") as f:
            files = {"file": ("turn.wav", f, "audio/wav")}
            data = {"duration_seconds": "3"}
            turn = httpx.post(
                f"{BASE}/api/student/languages/speaking/conversation/turn",
                headers=headers,
                files=files,
                data=data,
                timeout=300,
            )
        body = turn.json() if turn.status_code == 200 else {}
        has_transcript = bool(body.get("transcript"))
        has_reply = bool(body.get("reply"))
        has_eval = bool(body.get("evaluation"))
        audio_url = body.get("reply_audio_url")
        pending = body.get("reply_audio_pending")
        record(
            "conversation_turn_e2e",
            turn.status_code == 200 and has_transcript and has_reply and has_eval,
            status=turn.status_code,
            transcript_preview=(body.get("transcript") or "")[:80],
            reply_preview=(body.get("reply") or "")[:120],
            estimated_cefr=body.get("evaluation", {}).get("estimated_cefr") if has_eval else None,
            coaching_note_ar=(body.get("evaluation") or {}).get("coaching_note_ar"),
        )
        record(
            "gemini_reply",
            has_reply,
            reply_preview=(body.get("reply") or "")[:120],
        )
        record(
            "whisper_transcription",
            has_transcript,
            transcript_preview=(body.get("transcript") or "")[:80],
        )
        if audio_url:
            audio = httpx.get(f"{BASE}{audio_url}" if audio_url.startswith("/") else audio_url, timeout=30)
            record(
                "xtts_reply_audio",
                audio.status_code == 200 and len(audio.content) > 1000,
                url=audio_url,
                bytes=len(audio.content),
            )
        elif pending:
            for _ in range(45):
                time.sleep(2)
                state = httpx.get(
                    f"{BASE}/api/student/languages/speaking/conversation",
                    headers=headers,
                    timeout=30,
                )
                msgs = state.json().get("messages", []) if state.status_code == 200 else []
                assistant = next(
                    (m for m in reversed(msgs) if m.get("role") == "assistant"),
                    None,
                )
                url = assistant.get("reply_audio_url") if assistant else None
                if url:
                    audio = httpx.get(f"{BASE}{url}" if url.startswith("/") else url, timeout=30)
                    record(
                        "xtts_reply_audio",
                        audio.status_code == 200 and len(audio.content) > 1000,
                        url=url,
                        bytes=len(audio.content),
                        polled=True,
                    )
                    return
            record("xtts_reply_audio", False, error="timed out waiting for reply audio")
        else:
            record("xtts_reply_audio", False, error="no reply_audio_url and not pending")
    except Exception as exc:
        record("conversation_turn_e2e", False, error=str(exc), traceback=traceback.format_exc()[-600:])


def check_language_module_regressions(headers: dict) -> None:
    endpoints = [
        ("hub", f"{BASE}/api/student/languages/hub"),
        ("reading", f"{BASE}/api/student/languages/reading"),
        ("listening", f"{BASE}/api/student/languages/listening"),
        ("writing", f"{BASE}/api/student/languages/writing"),
        ("vocabulary", f"{BASE}/api/student/languages/vocabulary"),
        ("progress", f"{BASE}/api/student/languages/progress"),
    ]
    for name, url in endpoints:
        try:
            r = httpx.get(url, headers=headers, timeout=30)
            record(f"regression_language_{name}", r.status_code == 200, status=r.status_code)
        except Exception as exc:
            record(f"regression_language_{name}", False, error=str(exc))


def check_services_up() -> bool:
  try:
    health = httpx.get(f"{BASE}/health", timeout=5)
    tts = httpx.get("http://127.0.0.1:8010/health", timeout=5)
    record("backend_health", health.status_code == 200, status=health.status_code)
    record("tts_worker_health", tts.status_code == 200, status=tts.status_code)
    return health.status_code == 200
  except Exception as exc:
    record("backend_health", False, error=str(exc))
    return False


async def main() -> int:
    check_frontend_files()
    check_frontend_build()
    if not check_services_up():
        REPORT["all_ok"] = all(c["ok"] for c in REPORT["checks"] if c["name"] in ("frontend_files", "frontend_build"))
        REPORT["note"] = "Backend/TTS not running — API e2e checks skipped"
        out = BACKEND / "scripts" / "phase3_verify_report.json"
        out.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(REPORT, ensure_ascii=False, indent=2))
        return 1

    token = login_token()
    if not token:
        record("auth_login", False)
    else:
        record("auth_login", True)
        headers = {"Authorization": f"Bearer {token}"}
        check_speaking_exercises(headers)
        check_conversation_state(headers)
        check_conversation_turn_e2e(headers)
        check_language_module_regressions(headers)

    REPORT["all_ok"] = all(c["ok"] for c in REPORT["checks"])
    out = BACKEND / "scripts" / "phase3_verify_report.json"
    out.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(REPORT, ensure_ascii=False, indent=2))
    return 0 if REPORT["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
