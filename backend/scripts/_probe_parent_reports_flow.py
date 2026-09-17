"""Full parent reports flow probe."""
from __future__ import annotations

import json
from pathlib import Path
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api"
PROXY = "http://127.0.0.1:5173/api"
OUT = Path(__file__).resolve().parent / "_probe_parent_reports_flow.out.json"


def call(method: str, url: str, *, token: str | None = None, data: dict | None = None) -> dict:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return {"ok": True, "status": resp.status, "body": raw[:600]}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "status": exc.code, "body": raw[:600]}
    except Exception as exc:
        return {"ok": False, "status": -1, "error": f"{type(exc).__name__}: {exc}"}


def main() -> None:
    out: dict = {}
    login = call("POST", f"{BASE}/auth/login", data={"email": "test.auth.parent@eduspark-test.dev", "password": "TestOnly123!"})
    out["login"] = login
    if login.get("status") != 200:
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    token = json.loads(login["body"])["access_token"]

    for label, base in [("direct", BASE), ("proxy", PROXY)]:
        students = call("GET", f"{base}/parent/students", token=token)
        out[f"students_{label}"] = students
        sid = None
        if students.get("status") == 200:
            arr = json.loads(students["body"])
            if arr:
                sid = arr[0]["id"]
        url = f"{base}/parent/historical-report?period=this_week"
        if sid is not None:
            url += f"&student_id={sid}"
        out[f"historical_{label}"] = call("GET", url, token=token)

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
