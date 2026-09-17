"""Read-only voice cloning pipeline investigation."""
import json
from pathlib import Path

import httpx
import psycopg2

OUT = Path(__file__).resolve().parent / "voice_investigation_out.json"
BASE = "http://127.0.0.1:8000"
PASSWORDS = ("teacher123", "password123", "changeme", "student123")


def login(email: str) -> str | None:
    for pwd in PASSWORDS:
        r = httpx.post(f"{BASE}/api/auth/login", json={"email": email, "password": pwd}, timeout=30)
        if r.status_code == 200:
            return r.json()["access_token"]
    return None


def main() -> None:
    report: dict = {}

    # Worker health
    try:
        w = httpx.get("http://127.0.0.1:8010/health", timeout=10)
        report["tts_worker"] = {"status_code": w.status_code, "body": w.json() if w.status_code == 200 else w.text[:300]}
    except Exception as exc:
        report["tts_worker"] = {"error": str(exc)}

    # Backend settings (via import)
    try:
        import sys

        backend_root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(backend_root))
        from app.core.config import get_settings

        s = get_settings()
        report["backend_settings"] = {
            "ENABLE_TTS": s.ENABLE_TTS,
            "TTS_PROVIDER": s.TTS_PROVIDER,
            "TTS_WORKER_URL": s.TTS_WORKER_URL,
            "TTS_OUTPUT_DIR": s.TTS_OUTPUT_DIR,
            "UPLOAD_DIR": s.UPLOAD_DIR,
            "VOICE_SAMPLE_MIN_SECONDS": s.VOICE_SAMPLE_MIN_SECONDS,
        }
    except Exception as exc:
        report["backend_settings"] = {"error": str(exc)}

    conn = psycopg2.connect(
        host="localhost", port=5432, user="postgres", password="changeme", dbname="eduspark"
    )
    cur = conn.cursor()

    cur.execute(
        """
        SELECT tvs.id, tvs.teacher_profile_id, tp.user_id, u.email,
               tvs.processing_status, tvs.storage_path, tvs.duration_seconds,
               tvs.error_message, tvs.uploaded_at,
               CASE WHEN tvs.transcript IS NOT NULL THEN LEFT(tvs.transcript, 80) ELSE NULL END
        FROM teacher_voice_samples tvs
        JOIN teacher_profiles tp ON tp.id = tvs.teacher_profile_id
        JOIN users u ON u.id = tp.user_id
        ORDER BY tvs.id DESC
        """
    )
    samples = []
    for row in cur.fetchall():
        storage = row[5]
        exists = Path(storage).exists() if storage else False
        samples.append(
            {
                "id": row[0],
                "teacher_profile_id": row[1],
                "teacher_user_id": row[2],
                "teacher_email": row[3],
                "processing_status": row[4],
                "storage_path": storage,
                "file_exists": exists,
                "duration_seconds": row[6],
                "error_message": row[7],
                "uploaded_at": str(row[8]),
                "transcript_preview": row[9],
            }
        )
    report["teacher_voice_samples"] = samples
    report["teacher_voice_samples_count"] = len(samples)
    report["ready_samples_count"] = sum(1 for s in samples if s["processing_status"] == "ready")

    cur.execute(
        """
        SELECT l.id, l.title, l.teacher_id, u.email, l.voice_path, l.status::text, c.id
        FROM lessons l
        JOIN users u ON u.id = l.teacher_id
        JOIN courses c ON c.id = l.course_id
        WHERE l.status::text = 'processed'
        ORDER BY l.id DESC
        LIMIT 10
        """
    )
    lessons = []
    for row in cur.fetchall():
        voice_path = row[4]
        lessons.append(
            {
                "lesson_id": row[0],
                "title": row[1],
                "teacher_id": row[2],
                "teacher_email": row[3],
                "lesson_voice_path": voice_path,
                "lesson_voice_exists": Path(voice_path).exists() if voice_path else False,
                "status": row[5],
                "course_id": row[6],
            }
        )
    report["processed_lessons"] = lessons

    cur.execute(
        """
        SELECT cm.id, cm.lesson_id, cm.student_id, LEFT(cm.content, 250), cm.created_at
        FROM chat_messages cm
        WHERE cm.role = 'ai'
        ORDER BY cm.id DESC
        LIMIT 5
        """
    )
    recent_ai = []
    for row in cur.fetchall():
        content = row[3] or ""
        recent_ai.append(
            {
                "id": row[0],
                "lesson_id": row[1],
                "student_id": row[2],
                "has_audio_marker": "EDUSPARK_AUDIO" in content,
                "content_preview": content[:200],
                "created_at": str(row[4]),
            }
        )
    report["recent_ai_messages"] = recent_ai

    conn.close()

    # Student chat probe
    student_email = "test.student@example.com"
    st = login(student_email)
    report["student_login"] = {"email": student_email, "ok": bool(st)}
    if st and lessons:
        lesson_id = lessons[0]["lesson_id"]
        chat = httpx.post(
            f"{BASE}/api/student/chat",
            json={"lesson_id": lesson_id, "message": "ما موضوع الدرس؟ أجب بجملة واحدة."},
            headers={"Authorization": f"Bearer {st}"},
            timeout=180,
        )
        report["student_chat"] = {"lesson_id": lesson_id, "status_code": chat.status_code}
        if chat.status_code == 200:
            body = chat.json()
            ai = [m for m in body.get("messages", []) if m.get("role") == "ai"]
            last = ai[-1] if ai else {}
            report["student_chat"].update(
                {
                    "audio_url_top_level": body.get("audio_url"),
                    "last_ai_audioUrl": last.get("audioUrl"),
                    "last_ai_text_preview": (last.get("text") or "")[:120],
                }
            )
        else:
            report["student_chat"]["error"] = chat.text[:400]

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(OUT))


if __name__ == "__main__":
    main()
