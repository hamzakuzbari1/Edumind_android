"""End-to-end API probe as parent user 23 (linked student 5)."""
from __future__ import annotations

import json
from pathlib import Path
import urllib.error
import urllib.request

from app.core.security import create_access_token

OUT = Path(__file__).resolve().parent / "_probe_parent23_api.out.json"
TOKEN = create_access_token({"sub": "23", "role": "parent"}, session_id=275)


def get(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return {"status": resp.status, "body_len": len(body), "preview": body[:250]}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "preview": exc.read(500).decode("utf-8", errors="replace")}
    except Exception as exc:
        return {"status": -1, "error": f"{type(exc).__name__}: {exc}"}


def main() -> None:
    out = {
        "students_direct": get("http://127.0.0.1:8000/api/parent/students"),
        "report_direct": get("http://127.0.0.1:8000/api/parent/historical-report?period=this_week&student_id=5"),
        "students_proxy": get("http://127.0.0.1:5173/api/parent/students"),
        "report_proxy": get("http://127.0.0.1:5173/api/parent/historical-report?period=this_week&student_id=5"),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
