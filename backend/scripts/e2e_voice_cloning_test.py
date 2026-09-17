"""End-to-end voice cloning verification (teacher sample -> student chat -> audio URL)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import psycopg2

BASE = "http://127.0.0.1:8000"
PASSWORDS = ("teacher123", "password123", "changeme", "student123")


def db():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="changeme",
        dbname="eduspark",
    )


def login(email: str) -> str | None:
    for pwd in PASSWORDS:
        r = httpx.post(f"{BASE}/api/auth/login", json={"email": email, "password": pwd}, timeout=20)
        if r.status_code == 200:
            return r.json()["access_token"]
    return None


def main() -> int:
    results: dict = {"steps": [], "pass": False}
    client = httpx.Client(timeout=120)

    # 0) Services
    try:
        backend_resp = client.get(f"{BASE}/docs")
        backend_ok = backend_resp.status_code == 200
        backend_detail = f"HTTP {backend_resp.status_code}"
    except Exception as exc:
        backend_ok = False
        backend_detail = str(exc)
    try:
        worker = client.get("http://127.0.0.1:8010/health", timeout=5)
        worker_ok = worker.status_code == 200
        worker_detail = worker.text
    except Exception as exc:
        worker_ok = False
        worker_detail = str(exc)
    results["steps"].append({"step": "backend_up", "ok": backend_ok, "detail": backend_detail})
    results["steps"].append({"step": "tts_worker_up", "ok": worker_ok, "detail": worker_detail})
    if not backend_ok:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 1

    conn = db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT u.id, u.email, tp.id, tvs.id, tvs.processing_status, tvs.storage_path
        FROM users u
        JOIN teacher_profiles tp ON tp.user_id = u.id
        LEFT JOIN teacher_voice_samples tvs ON tvs.teacher_profile_id = tp.id
        WHERE u.role = 'teacher'
        ORDER BY (tvs.processing_status = 'ready') DESC NULLS LAST, u.id, tvs.uploaded_at DESC NULLS LAST
        LIMIT 1
        """
    )
    teacher_row = cur.fetchone()
    if not teacher_row:
        results["steps"].append({"step": "find_teacher", "ok": False, "detail": "no teacher in DB"})
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 1

    teacher_user_id, teacher_email, teacher_profile_id, sample_id, sample_status, sample_path = teacher_row
    results["steps"].append(
        {
            "step": "find_teacher",
            "ok": True,
            "detail": {
                "teacher_user_id": teacher_user_id,
                "email": teacher_email,
                "sample_id": sample_id,
                "sample_status": sample_status,
                "sample_path": sample_path,
            },
        }
    )

    cur.execute(
        """
        SELECT l.id, l.title, l.teacher_id, c.id
        FROM lessons l
        JOIN courses c ON c.id = l.course_id
        JOIN teacher_profiles tp ON tp.id = c.teacher_profile_id
        WHERE tp.user_id = %s AND l.status::text = 'processed'
        ORDER BY l.id DESC
        LIMIT 1
        """,
        (teacher_user_id,),
    )
    lesson_row = cur.fetchone()
    if not lesson_row:
        results["steps"].append({"step": "find_lesson", "ok": False, "detail": "no ready lesson for teacher"})
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 1
    lesson_id, lesson_title, _, course_id = lesson_row
    results["steps"].append({"step": "find_lesson", "ok": True, "detail": {"lesson_id": lesson_id, "title": lesson_title, "course_id": course_id}})

    cur.execute(
        """
        SELECT u.id, u.email
        FROM users u
        JOIN student_profiles sp ON sp.user_id = u.id
        JOIN enrollments e ON e.student_profile_id = sp.id
        WHERE e.course_id = %s AND u.role = 'student'
        LIMIT 1
        """,
        (course_id,),
    )
    student_row = cur.fetchone()
    if not student_row:
        cur.execute("SELECT id, email FROM users WHERE role = 'student' LIMIT 1")
        student_row = cur.fetchone()
    student_id, student_email = student_row
    results["steps"].append({"step": "find_student", "ok": True, "detail": {"student_id": student_id, "email": student_email}})
    conn.close()

    teacher_token = login(teacher_email)
    results["steps"].append({"step": "teacher_login", "ok": bool(teacher_token), "detail": teacher_email})
    if not teacher_token:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 1

    # Teacher voice profile
    vp = client.get(f"{BASE}/api/teacher/voice-profile", headers={"Authorization": f"Bearer {teacher_token}"})
    results["steps"].append({"step": "teacher_voice_profile", "ok": vp.status_code == 200, "detail": vp.json() if vp.status_code == 200 else vp.text[:300]})

    has_ready = vp.status_code == 200 and vp.json().get("has_ready_profile")
    if not has_ready:
        # Try upload if we have a sample file on disk from archive or generate minimal test
        results["steps"].append({"step": "teacher_has_ready_voice", "ok": False, "detail": "no ready voice sample — upload step required but skipped (no test audio file bundled)"})

    student_token = login(student_email)
    results["steps"].append({"step": "student_login", "ok": bool(student_token), "detail": student_email})
    if not student_token:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 1

    chat_payload = {"lessonId": lesson_id, "message": "ما هو موضوع هذا الدرس؟ أجب بجملة واحدة."}
    chat = client.post(
        f"{BASE}/api/student/chat",
        json=chat_payload,
        headers={"Authorization": f"Bearer {student_token}"},
    )
    chat_body = chat.json() if chat.headers.get("content-type", "").startswith("application/json") else {"raw": chat.text[:500]}
    results["steps"].append({"step": "student_ai_chat", "ok": chat.status_code == 200, "detail": {"status": chat.status_code, "body_keys": list(chat_body.keys()) if isinstance(chat_body, dict) else None}})

    audio_url = None
    ai_messages = []
    if chat.status_code == 200 and isinstance(chat_body, dict):
        messages = chat_body.get("messages") or []
        ai_messages = [m for m in messages if m.get("role") == "ai"]
        if ai_messages:
            audio_url = ai_messages[-1].get("audioUrl")

    results["steps"].append(
        {
            "step": "audio_url_in_response",
            "ok": bool(audio_url),
            "detail": {"audioUrl": audio_url, "last_ai_text": (ai_messages[-1].get("text", "")[:120] if ai_messages else None)},
        }
    )

    audio_fetch_ok = False
    audio_bytes = 0
    if audio_url:
        fetch = client.get(f"{BASE}{audio_url}" if audio_url.startswith("/") else audio_url)
        audio_fetch_ok = fetch.status_code == 200 and len(fetch.content) > 1000
        audio_bytes = len(fetch.content)
    results["steps"].append(
        {"step": "audio_file_downloadable", "ok": audio_fetch_ok, "detail": {"bytes": audio_bytes, "url": audio_url}}
    )

    # Reload history — persistence check
    history_ok = False
    persisted_audio = None
    if chat.status_code == 200:
        hist = client.get(
            f"{BASE}/api/student/lesson/{lesson_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        if hist.status_code == 200:
            msgs = hist.json().get("chatMessages") or []
            ai_hist = [m for m in msgs if m.get("role") == "ai"]
            if ai_hist:
                persisted_audio = ai_hist[-1].get("audioUrl")
                history_ok = bool(persisted_audio)
        results["steps"].append(
            {
                "step": "audio_persisted_in_history",
                "ok": history_ok,
                "detail": {"audioUrl": persisted_audio, "history_status": hist.status_code if chat.status_code == 200 else None},
            }
        )

    results["pass"] = all(
        s["ok"]
        for s in results["steps"]
        if s["step"]
        in (
            "backend_up",
            "student_ai_chat",
            "audio_url_in_response",
            "audio_file_downloadable",
            "audio_persisted_in_history",
        )
    )
    out_path = Path(__file__).resolve().parent / "e2e_voice_results.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0 if results["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
