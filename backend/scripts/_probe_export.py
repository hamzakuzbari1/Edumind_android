"""Probe export endpoint for parent 23."""
from __future__ import annotations

import json
from pathlib import Path
import urllib.error
import urllib.request

from app.core.security import create_access_token

OUT = Path(__file__).resolve().parent / "_probe_export.out.json"
TOKEN = create_access_token({"sub": "23", "role": "parent"}, session_id=275)


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = resp.read(256)
            return {"status": resp.status, "content_type": resp.headers.get("Content-Type"), "body_len_hint": len(body), "starts_with": body[:20].hex()}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "body": exc.read(300).decode("utf-8", errors="replace")}
    except Exception as exc:
        return {"status": -1, "error": f"{type(exc).__name__}: {exc}"}


def main() -> None:
    base = "http://127.0.0.1:5173/api/parent/historical-report/export"
    out = {
        "csv": get(f"{base}?format=csv&period=this_week&student_id=5"),
        "pdf": get(f"{base}?format=pdf&period=this_week&student_id=5"),
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
