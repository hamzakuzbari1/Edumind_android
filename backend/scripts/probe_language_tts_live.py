"""Live runtime probe for Phase 9.3 TTS + listening (port 8000)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "public"


def main() -> int:
    base = "http://127.0.0.1:8000"
    out: dict[str, object] = {}

    try:
        r = httpx.get(f"{base}/openapi.json", timeout=10)
        out["openapi_status"] = r.status_code
        if r.status_code == 200:
            out["openapi_paths"] = len(r.json().get("paths", {}))
    except Exception as exc:
        print(f"openapi probe failed: {exc}")
        return 1

    placement = PUBLIC / "language-assets" / "en" / "placement" / "listening" / "q1.mp3"
    out["placement_q1_bytes"] = placement.stat().st_size if placement.is_file() else 0

    try:
        asset = httpx.get(f"http://127.0.0.1:5173/language-assets/en/placement/listening/q1.mp3", timeout=10)
        out["vite_static_q1_status"] = asset.status_code
    except Exception:
        out["vite_static_q1_status"] = "unreachable"

    login = httpx.post(
        f"{base}/api/auth/login",
        json={"email": "test.student@example.com", "password": "changeme"},
        timeout=15,
    )
    out["login_status"] = login.status_code
    if login.status_code != 200:
        print(json.dumps(out, indent=2))
        return 1

    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    listing = httpx.get(f"{base}/api/student/languages/listening", headers=headers, timeout=15)
    out["listening_list_status"] = listing.status_code
    lessons = listing.json().get("lessons") or [] if listing.status_code == 200 else []
    out["listening_lesson_count"] = len(lessons)

    detail_id = lessons[0]["id"] if lessons else None
    if detail_id:
        detail = httpx.get(
            f"{base}/api/student/languages/listening/{detail_id}",
            headers=headers,
            timeout=60,
        )
        out["listening_detail_status"] = detail.status_code
        if detail.status_code == 200:
            body = detail.json()
            out["audio_available"] = body.get("audio_available")
            out["audio_url"] = body.get("audio_url")
            if body.get("audio_url"):
                audio = httpx.get(f"{base}{body['audio_url']}", timeout=30)
                out["audio_fetch_status"] = audio.status_code
                out["audio_content_type"] = audio.headers.get("content-type")
                out["audio_bytes"] = len(audio.content)

    print("=== Phase 9.3 Live Runtime Probe ===")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    ok = (
        out.get("openapi_paths", 0) >= 274
        and out.get("placement_q1_bytes", 0) > 0
        and out.get("listening_detail_status") == 200
        and out.get("audio_available") is True
        and (out.get("audio_fetch_status") == 200 or out.get("vite_static_q1_status") == 200)
    )
    print(f"\nOverall: {'PASS' if ok else 'PARTIAL/FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
