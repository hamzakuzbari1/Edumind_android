"""Verify teacher voice upload after requirements-voice.txt install."""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psycopg2

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

OUT = Path(__file__).resolve().parent / "voice_upload_verify_results.json"
BASE = "http://127.0.0.1:8000"
TEACHER_EMAIL = "yaser@gmail.com"
TEACHER_USER_ID = 16
TEST_PASSWORD = "changeme"
SPEECH_WAV = Path(__file__).resolve().parent / "verify_teacher_speech.wav"


def db_rows() -> list[dict]:
    conn = psycopg2.connect(
        host="localhost", port=5432, user="postgres", password="changeme", dbname="eduspark"
    )
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, teacher_profile_id, processing_status, storage_path, error_message, duration_seconds
        FROM teacher_voice_samples
        ORDER BY id DESC
        LIMIT 5
        """
    )
    rows = []
    for r in cur.fetchall():
        rows.append(
            {
                "id": r[0],
                "teacher_profile_id": r[1],
                "processing_status": r[2],
                "storage_path": r[3],
                "file_exists": Path(r[3]).exists() if r[3] else False,
                "error_message": r[4],
                "duration_seconds": r[5],
            }
        )
    conn.close()
    return rows


def ensure_teacher_password() -> None:
    import bcrypt

    hashed = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt()).decode()
    conn = psycopg2.connect(
        host="localhost", port=5432, user="postgres", password="changeme", dbname="eduspark"
    )
    cur = conn.cursor()
    cur.execute("UPDATE users SET hashed_password = %s WHERE email = %s", (hashed, TEACHER_EMAIL))
    conn.commit()
    conn.close()


def generate_speech_wav() -> None:
    import imageio_ffmpeg

    short = SPEECH_WAV.with_suffix(".short.wav")
    text = (
        "مرحباً، أنا معلم في منصة إيدو سبARK. "
        "سأشرح اليوم درساً في العلوم عن التركيب الضوئي وكيف تصنع النباتات غذاءها. "
        "الطلاب يجب أن يفهموا أن الضوء والماء وثاني أكسيد الكربون ضروريون للحياة. "
    ) * 12
    ps = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate = -2
$s.SetOutputToWaveFile('{short.as_posix()}')
$s.Speak(@'
{text}
'@)
$s.Dispose()
"""
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, capture_output=True, text=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-stream_loop", "-1", "-i", str(short), "-t", "65", "-ac", "1", "-ar", "24000", str(SPEECH_WAV)],
        check=True,
    )


def login() -> str:
    r = httpx.post(
        f"{BASE}/api/auth/login",
        json={"email": TEACHER_EMAIL, "password": TEST_PASSWORD},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def upload_http(token: str) -> dict:
    with SPEECH_WAV.open("rb") as f:
        r = httpx.post(
            f"{BASE}/api/teacher/voice-sample",
            files={"file": ("verify_teacher_speech.wav", f, "audio/wav")},
            headers={"Authorization": f"Bearer {token}"},
            timeout=180,
        )
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}
    return {"status_code": r.status_code, "body": body}


def poll_ready(sample_id: int, timeout_s: int = 300) -> dict:
    deadline = time.time() + timeout_s
    history = []
    while time.time() < deadline:
        rows = db_rows()
        row = next((x for x in rows if x["id"] == sample_id), None)
        if row:
            history.append(row["processing_status"])
            if row["processing_status"] in ("ready", "failed"):
                return {"final": row, "history": history}
        time.sleep(3)
    return {"final": row if row else None, "history": history, "timeout": True}


def student_chat_audio_url(lesson_id: int = 79) -> dict:
    st = httpx.post(
        f"{BASE}/api/auth/login",
        json={"email": "test.student@example.com", "password": TEST_PASSWORD},
        timeout=30,
    )
    st.raise_for_status()
    token = st.json()["access_token"]
    chat = httpx.post(
        f"{BASE}/api/student/chat",
        json={"lesson_id": lesson_id, "message": "ما موضوع الدرس؟ أجب بجملة واحدة."},
        headers={"Authorization": f"Bearer {token}"},
        timeout=180,
    )
    out = {"status_code": chat.status_code}
    if chat.status_code == 200:
        body = chat.json()
        ai = [m for m in body.get("messages", []) if m.get("role") == "ai"]
        last = ai[-1] if ai else {}
        out["audio_url"] = body.get("audio_url") or last.get("audioUrl")
        out["last_ai_text"] = (last.get("text") or "")[:120]
    else:
        out["error"] = chat.text[:400]
    return out


def main() -> None:
    report: dict = {"steps": []}

    from faster_whisper import WhisperModel  # noqa: F401
    import imageio_ffmpeg

    report["steps"].append(
        {
            "step": "imports",
            "ok": True,
            "ffmpeg": imageio_ffmpeg.get_ffmpeg_exe(),
        }
    )

    if not SPEECH_WAV.exists() or SPEECH_WAV.stat().st_size < 500_000:
        generate_speech_wav()
    else:
        from app.services.voice_validation_service import validate_voice_sample as _val

        if _val(SPEECH_WAV).duration_seconds < 60:
            generate_speech_wav()
    report["steps"].append(
        {
            "step": "speech_fixture",
            "ok": SPEECH_WAV.exists(),
            "bytes": SPEECH_WAV.stat().st_size if SPEECH_WAV.exists() else 0,
        }
    )

    from app.services.voice_validation_service import validate_voice_sample

    val = validate_voice_sample(SPEECH_WAV)
    report["steps"].append(
        {
            "step": "validate_voice_sample",
            "ok": val.ok,
            "duration_seconds": val.duration_seconds,
            "error": val.error,
        }
    )

    report["db_before"] = db_rows()
    ensure_teacher_password()
    token = login()
    upload = upload_http(token)
    report["steps"].append({"step": "http_upload", "ok": upload["status_code"] == 200, **upload})

    sample_id = None
    if upload["status_code"] == 200 and isinstance(upload["body"], dict):
        sample_id = upload["body"].get("id")

    report["db_after_upload"] = db_rows()

    if sample_id:
        poll = poll_ready(sample_id)
        report["steps"].append({"step": "processing_poll", **poll})
        report["db_final"] = db_rows()

        if poll.get("final", {}).get("processing_status") == "ready":
            # lesson 79 is teacher 16; use a lesson for teacher 44 if exists
            conn = psycopg2.connect(
                host="localhost", port=5432, user="postgres", password="changeme", dbname="eduspark"
            )
            cur = conn.cursor()
            cur.execute(
                """
                SELECT l.id FROM lessons l
                JOIN courses c ON c.id = l.course_id
                JOIN teacher_profiles tp ON tp.id = c.teacher_profile_id
                WHERE tp.user_id = %s AND l.status::text = 'processed'
                ORDER BY l.id DESC LIMIT 1
                """,
                (TEACHER_USER_ID,),
            )
            row = cur.fetchone()
            conn.close()
            lesson_id = row[0] if row else 79
            report["steps"].append(
                {
                    "step": "student_chat",
                    **student_chat_audio_url(lesson_id),
                }
            )
    else:
        report["steps"].append({"step": "student_chat", "skipped": "sample not ready"})

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(str(OUT))
    ok = all(s.get("ok", True) for s in report["steps"] if s["step"] in ("imports", "validate_voice_sample", "http_upload"))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
