"""Probe parent historical-report endpoint (direct + via Vite proxy)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import urllib.error
import urllib.request

BASE_DIRECT = "http://127.0.0.1:8000/api"
BASE_PROXY = "http://127.0.0.1:5173/api"
EMAIL = "test.auth.parent@eduspark-test.dev"
PASSWORD = "TestOnly123!"
OUT = Path(__file__).resolve().parent / "_probe_historical_report.out.json"


def req(method: str, url: str, *, token: str | None = None, data: dict | None = None) -> tuple[int, str]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return -1, f"{type(exc).__name__}: {exc}"


def main() -> None:
    out: dict = {}
    status, body = req("POST", f"{BASE_DIRECT}/auth/login", data={"email": EMAIL, "password": PASSWORD})
    out["login"] = {"status": status, "body_preview": body[:300]}
    if status != 200:
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        sys.exit(1)

    token = json.loads(body)["access_token"]
    out["token_len"] = len(token)

    for label, base in [("direct", BASE_DIRECT), ("vite_proxy", BASE_PROXY)]:
        status, body = req(
            "GET",
            f"{base}/parent/historical-report?period=this_week",
            token=token,
        )
        out[f"historical_report_{label}"] = {
            "url": f"{base}/parent/historical-report?period=this_week",
            "status": status,
            "body_preview": body[:400],
        }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
