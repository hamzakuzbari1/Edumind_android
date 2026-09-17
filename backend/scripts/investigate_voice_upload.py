"""Investigate teacher voice upload — no code changes."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import httpx
import psycopg2

OUT = Path(__file__).resolve().parent / "voice_upload_investigation.json"
BASE = "http://127.0.0.1:8000"
PASSWORDS = ("teacher123", "password123", "changeme", "student123", "changeme")


def login_teachers() -> list[dict]:
    conn = psycopg2.connect(
        host="localhost", port=5432, user="postgres", password="changeme", dbname="eduspark"
    )
    cur = conn.cursor()
    cur.execute("SELECT id, email FROM users WHERE role = 'teacher' ORDER BY id")
    teachers = cur.fetchall()
    conn.close()
    results = []
    for tid, email in teachers:
        token = None
        pwd_used = None
        for pwd in PASSWORDS:
            r = httpx.post(f"{BASE}/api/auth/login", json={"email": email, "password": pwd}, timeout=30)
            if r.status_code == 200:
                token = r.json()["access_token"]
                pwd_used = pwd
                break
        results.append({"user_id": tid, "email": email, "login_ok": bool(token), "password": pwd_used, "token": token})
    return results


def make_wav(path: Path, seconds: float, freq: float = 440.0, amplitude: float = 0.3) -> None:
    import math

    rate = 24000
    n = int(rate * seconds)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        for i in range(n):
            val = int(amplitude * 32767 * math.sin(2 * math.pi * freq * (i / rate)))
            wf.writeframesraw(val.to_bytes(2, "little", signed=True))


def upload_file(token: str, file_path: Path) -> dict:
    with file_path.open("rb") as f:
        files = {"file": (file_path.name, f, "audio/wav")}
        r = httpx.post(
            f"{BASE}/api/teacher/voice-sample",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
            timeout=120,
        )
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}
    return {"status_code": r.status_code, "body": body, "file": str(file_path), "size_bytes": file_path.stat().st_size}


def validate_local(path: Path) -> dict:
    backend_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_root))
    from app.services.voice_validation_service import validate_voice_sample

    result = validate_voice_sample(path)
    return {
        "ok": result.ok,
        "duration_seconds": result.duration_seconds,
        "error": result.error,
    }


def db_count() -> int:
    conn = psycopg2.connect(
        host="localhost", port=5432, user="postgres", password="changeme", dbname="eduspark"
    )
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM teacher_voice_samples")
    n = cur.fetchone()[0]
    conn.close()
    return n


def main() -> None:
    report: dict = {"db_rows_before": db_count(), "tests": []}

    teachers = login_teachers()
    report["teacher_logins"] = [{k: v for k, v in t.items() if k != "token"} for t in teachers]
    token = next((t["token"] for t in teachers if t["token"]), None)
    report["usable_teacher_token"] = bool(token)

    tmp = Path(tempfile.mkdtemp(prefix="eduspark_voice_test_"))

    cases = [
        ("tiny_1kb", 0.05),
        ("short_10s", 10),
        ("short_30s", 30),
        ("min_59s", 59),
        ("min_60s_tone", 60),
        ("min_65s_tone", 65),
    ]

    for name, seconds in cases:
        wav = tmp / f"{name}.wav"
        make_wav(wav, seconds)
        local_val = validate_local(wav)
        entry = {"case": name, "seconds": seconds, "local_validation": local_val}
        if token:
            before = db_count()
            entry["upload"] = upload_file(token, wav)
            entry["db_rows_after"] = db_count()
            entry["row_created"] = db_count() > before
        report["tests"].append(entry)

    # Optional: ffmpeg speech-like file if ffmpeg available
    speech_wav = tmp / "speech_65s.wav"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=300:duration=65",
                "-ac",
                "1",
                "-ar",
                "24000",
                str(speech_wav),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        local_val = validate_local(speech_wav)
        entry = {"case": "ffmpeg_sine_65s", "seconds": 65, "local_validation": local_val}
        if token:
            before = db_count()
            entry["upload"] = upload_file(token, speech_wav)
            entry["db_rows_after"] = db_count()
            entry["row_created"] = db_count() > before
        report["tests"].append(entry)
    except Exception as exc:
        report["ffmpeg_test_error"] = str(exc)

    report["db_rows_final"] = db_count()
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(OUT))


if __name__ == "__main__":
    main()
